#http://pwoah7foa6au2pul.onion

from __future__ import absolute_import
import scrapy
from scrapy.http import FormRequest,Request
from scrapy.shell import inspect_response
from scrapyprj.spiders.ForumSpider import ForumSpider
from scrapyprj.database.orm import *

import scrapyprj.spider_folder.template_spider.items as items  



class AlphabayForum(ForumSpider):
    name = "template_spider"
    handle_httpstatus_list = [403]  # Leaves these response code reach our spider instead of being dropped by a middleware.
    
    # Define the pieline we want for this spider. See that we refer to the map2db pipeline which is specific to this spider.
    custom_settings = {
        'ITEM_PIPELINES': {
            'scrapyprj.spider_folder.template_spider.pipelines.map2db.map2db': 400,    # Convert from Items to Models
            'scrapyprj.pipelines.save2db.save2db': 401                  # Sends models to DatabaseDAO. DatabaseDAO must be explicitly flushed from spider.  self.dao.flush(Model)
        }
    }

    def __init__(self, *args, **kwargs):
        super(self.__class__, self).__init__(*args, **kwargs)   # Call constructor

    def start_requests(self):               # Scrapy looks for this function
        yield self.make_request('page1')    # First request is yielded here.

    
    def make_request(self, reqtype, **kwargs):
        
        # Replace the URl with a fully qualified Url
        if 'url' in kwargs:
            kwargs['url'] = self.make_url(kwargs['url'])    

        if reqtype == 'page1':
            req = Request(self.make_url('MyResource1'))                 # See   spider_folder.template_spider.settings

        elif reqtype == 'page2':
            req = Request(self.make_url('MyResource2')) 

        elif reqtype == 'dologin':
            req = Request(self.make_url('LoginResource'))               # Custom callback. Will not go to "parse"
            req.meta['req_once_logged'] = kwargs['req_once_logged']     # meta field is available in the response. Parsing function shall re-yield the same request after login 
                                                                    
        else:
            raise Exception('Unsuported request type ' + reqtype)

        req.meta['reqtype'] = reqtype   # We tell the type so we can call the right parsing function afterwards
        req.meta['proxy'] = self.proxy  #meta[proxy] is handled by scrapy. self.proxy is set by the Parent Class

        return req
    
    # All request are sent to this callback. Proposed architecure goes as follow.
    def parse(self, response):
        if not self.islogged(response):
            yield self.make_request(reqtype='dologin', req_once_logged=response.request);  # We try to login and save the original request
        else : 
            if response.meta['reqtype'] == 'page1':
                for x in self.parse_page1(response) : yield x
            elif  response.meta['reqtype'] == 'page2':
                for x in self.parse_page2(response) : yield x
            elif response.meta['reqtype'] == 'dologin':
                for x in self.parse_loginresponse(response) : yield x

    # This example parse only for new request
    def parse_page1(self, response):
        threadlinks = response.css("a.threadlinks::attr(href)") # Example of selector.
        for threadlink in threadlinks:
            if self.shouldcrawl('thread') :                      # Helper defined in ForumSpider. Call it before yielding a request. That will make the spider follow the rules in the command line tool.
                yield self.make_request(reqtype='page2', url=threadlink.extract())

        messagelinks = response.css("a.message::attr(href)")    
        messagedate = response.css("....")                      # Find the date
        for messagelink in messagelinks:
            if self.shouldcrawl('message', messagedate):         # The date is used for delta crawl.
                yield self.make_request(reqtype='page2', url=threadlink.extract())

    # This example parse items as well as request.
    def parse_page2(self, response):
        # Since there is foreign key to respect. We first yield the items, flush the database que, then yield request. That will avoid race conditions.

        thread = template_spider.items.Thread()
        thread['author_username'] = response.css("#user h1").extract_first()  # Example
        thread['externalid'] = response.css("#post .content").extract_first()
        # etc.
        # Fill the item

        yield thread  # Send to pipeline

        self.dao.flush(models.Thread)  # Force the DAO to write the object into the database. We need this to make foreign key afterward.

        nextpage = response.css("a.nextpage::attr(href)").extract_first()               
        if self.shouldcrawl('Message'):
            yield self.make_request(reqtype='page3', url=nextpage)


    def parse_loginresponse(self, response):
        if self.islogged(response):
            yield response.meta['req_once_logged']
        else :   
            pass    # login failed. Logic is site specific.
                
    def islogged(self, response):
        # Site specific logic. Analyze response to deduce if we are logged.
        return logged


    ###### Required methods #######
    # The 2 followings methods allow our custom crawler the reload users after each crawl and also allow thread indexing.
    # Convert a PeeWee Model into a request for this site.

    def make_thread_request(self, thread):  # Has to be defined to make multi instance works.
        return self.make_request(reqtype='threadpage', url=thread.fullurl, threadid=thread.external_id)

    def make_user_request(self, user):      # Has to be defined to make multi instance works.
        return self.make_request(reqtype='userprofile', url=self.make_url(user.relativeurl))




