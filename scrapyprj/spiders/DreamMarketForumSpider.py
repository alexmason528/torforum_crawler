#http://pwoah7foa6au2pul.onion

from __future__ import absolute_import
import scrapy
from scrapy.http import FormRequest,Request
from scrapy.shell import inspect_response
from scrapyprj.spiders.ForumSpider import ForumSpider
from scrapyprj.database.orm import *
import scrapyprj.database.forums.orm.models as models
import scrapyprj.spider_folder.dreammarket_forum.items as items
from datetime import datetime, timedelta
from urlparse import urlparse, parse_qsl
import logging
import time
import hashlib 
import traceback
import re
import pytz
import dateutil
from IPython import embed

class DreamMarketForumSpider(ForumSpider):
    name = "dreammarket_forum"
    handle_httpstatus_list = [403]
    

    custom_settings = {
        'ITEM_PIPELINES': {
            'scrapyprj.spider_folder.dreammarket_forum.pipelines.map2db.map2db': 400,    # Convert from Items to Models
            'scrapyprj.pipelines.save2db.save2db': 401                  # Sends models to DatabaseDAO. DatabaseDAO must be explicitly flushed from spider.  self.dao.flush(Model)
        },
        'MAX_LOGIN_RETRY' : 10
    }

    def __init__(self, *args, **kwargs):
        super(self.__class__, self).__init__(*args, **kwargs)

        self.logintrial = 0

        self.parse_handlers = {
                'index'         : self.parse_index,
                'dologin'       : self.parse_index,
                'threadlisting' : self.parse_thread_listing,
                'thread'        : self.parse_thread,
                'userprofile'   : self.parse_userprofile
            }

    def start_requests(self):
        yield self.make_request('index')

    def make_request(self, reqtype,  **kwargs):
        
        if 'url' in kwargs:
            kwargs['url'] = self.make_url(kwargs['url'])

        if reqtype == 'index':
            req = Request(self.make_url('index'), dont_filter=True)
        elif reqtype == 'loginpage':
            req = Request(self.make_url('loginpage'), dont_filter=True)
        elif reqtype == 'dologin':
            req = self.craft_login_request_from_form(kwargs['response'])
            req.dont_filter=True
        elif reqtype == 'captcha_img':
            req = Request(self.make_url(kwargs['url']), dont_filter=True)
        elif reqtype in ['threadlisting', 'thread', 'userprofile']:
            req = Request(self.make_url(kwargs['url']))
        else:
            raise Exception('Unsuported request type ' + reqtype)

        req.meta['reqtype'] = reqtype   # We tell the type so that we can redo it if login is required
        req.meta['proxy'] = self.proxy  #meta[proxy] is handled by scrapy.

        return req
   
    def parse(self, response):
        if not self.islogged(response):
            if self.is_login_page(response):
                if self.logintrial > self.settings['MAX_LOGIN_RETRY']:
                    raise Exception("Too many failed login trials. Giving up.")
                self.logger.info("Trying to login.")
                self.logintrial += 1

                req_once_logged = response.meta['req_once_logged'] if 'req_once_logged'  in response.meta else response.request 
                
                yield self.make_request(reqtype='dologin',response=response, req_once_logged=req_once_logged);  # We try to login and save the original request
            else:
                self.logger.info("Not logged, going to login page.")
                yield self.make_request(reqtype='loginpage', req_once_logged=response.request);

        else : 
            self.logintrial = 0
            it = self.parse_handlers[response.meta['reqtype']].__call__(response)
            if it:
                for x in it:
                    if x != None:
                        yield x

    def parse_index(self, response):
        for line in response.css("#brdmain tbody tr"):
            link = line.css("h3>a::attr(href)").extract_first()
            
            yield self.make_request('threadlisting', url=link);
    
    def parse_thread_listing(self, response):
        oldest_post = datetime.utcnow()
        threads_requests = []
        
        for line in response.css("#brdmain tbody tr"):
            threaditem = items.Thread()
            title =  self.get_text(line.css("td:first-child a"))

            last_post_time = self.parse_timestr(self.get_text(line.css("td:last-child a")))
            if last_post_time:
                oldest_post = min(oldest_post, last_post_time)
            

            threadlinkobj = next(iter(line.css("td:first-child a") or []), None)
            if threadlinkobj:
                threadlinkhref = threadlinkobj.xpath("@href").extract_first() if threadlinkobj else None
                threaditem['title'] = self.get_text(threadlinkobj)
                threaditem['relativeurl'] = threadlinkhref
                threaditem['fullurl']   = self.make_url(threadlinkhref)
                
                threaditem['threadid'] = self.get_url_param(threaditem['fullurl'], 'id')

                byuser = self.get_text(line.css("td:first-child span.byuser"))
                m = re.match("by (.+)", byuser)
                if m:
                    threaditem['author_username'] = m.group(1)
                
                threaditem['last_update'] = last_post_time
                
                
                
                threaditem['replies']   = self.get_text(line.css("td:nth-child(2)"))
                threaditem['views']     = self.get_text(line.css("td:nth-child(3)"))
                print threaditem
                if self.shouldcrawl('thread', last_post_time):
                    threads_requests.append(self.make_request('thread', url=threadlinkhref))


        for req in threads_requests:
            yield req

        if self.shouldcrawl('thread', oldest_post):
            next_page_url = response.css("#brdmain .pagelink a[rel='next']::attr(href)").extract_first()
            if next_page_url:
                yield self.make_request('threadlisting', url=next_page_url)


    def parse_thread(self, response):
        oldest_post = datetime.utcnow()
        requests = []
        threadid =  self.get_url_param(response.url, 'id')
        posts = response.css("#brdmain div.blockpost")
        for post in posts:
            try:
                messageitem = items.Message()
                posttime = self.parse_timestr(self.get_text(post.css("h2 a")))
                if posttime:
                    oldest_post = min(oldest_post, posttime)

                userprofile_link = post.css(".postleft dt:first-child a::attr(href)").extract_first()
                messageitem['author_username'] = self.get_text(post.css(".postleft dt:first-child a"))
                messageitem['postid'] = post.xpath("@id").extract_first()
                messageitem['threadid'] = threadid

                msg = post.css("div.postmsg")
                messageitem['contenttext'] = self.get_text(msg)
                messageitem['contenthtml'] = msg.extract_first()

                yield messageitem

                if userprofile_link and self.shouldcrawl('user'):
                    requests.append(self.make_request('userprofile', url = userprofile_link))
            except e:
                self.logger.warning("Invalid thread page. %s" % e)

        self.dao.flush(models.Message)

        for req in requests:
            yield requests;

        if self.shouldcrawl('message', oldest_post):
            next_page_url = response.css("#brdmain .pagelink a[rel='next']::attr(href)").extract_first()
            if next_page_url:
                yield self.make_request('thread', url=next_page_url)

    def parse_userprofile(self, response):
        user = items.User()
        dts = response.css("#viewprofile dl dt")
        
        for dt in dts:
            key = self.get_text(dt).lower()
            ddtext = self.get_text(dt.xpath('following-sibling::dd[1]'))

            if key == 'username':
                user['username'] = ddtext
            elif key == 'title':
                user['title'] = ddtext
            elif key == 'registered':
                user['joined_on'] = self.parse_timestr(ddtext)
            elif key == 'last post':
                user['last_post'] = self.parse_timestr(ddtext)
            elif key == 'posts':
                m = re.match("^(\d+).+", ddtext)
                if m:
                    user['post_count'] = m.group(1)
            elif key == 'signature':
                user['signature'] = ddtext
            elif key == 'location':
                user['location'] = ddtext
            elif key == 'website':
                user['website'] = ddtext
            elif key in ['avatar', 'email']:
                pass
            else:
                self.logger.warning('New information found on use profile page : %s' % key)

        yield user

    def craft_login_request_from_form(self, response):
        data = {
            'req_username' : self.login['username'],
            'req_password' : self.login['password']
        }
        req = FormRequest.from_response(response, formdata=data)

        captcha_src = response.css("form#login img::attr(src)").extract_first()

        req.meta['captcha'] = {        # CaptchaMiddleware will take care of that.
            'request' : self.make_request('captcha_img', url=captcha_src),
            'name' : 'inpcaptch',    # Preprocess image to extract what's within the rectangle
            'preprocess' : 'DreamMarketRectangleCropper'
            }

        return req


    def parse_timestr(self, timestr):
        last_post_time = None
        try:
            timestr = timestr.lower()
            timestr = timestr.replace('today', str(self.localnow().date()))
            timestr = timestr.replace('yesterday', str(self.localnow().date() - timedelta(days=1)))
            last_post_time = self.to_utc(dateutil.parser.parse(timestr))
        except:
            if timestr:
                self.logger.warning("Could not determine time from this string : '%s'. Ignoring" % timestr)
        return last_post_time

    def islogged(self, response):
        contenttext = self.get_text(response.css("#brdwelcome"))
        if 'Logged in as' in contenttext:
            return True
        return False

    def is_login_page(self, response):
        if len(response.css("form#login")) > 0:
            return True
        return False

    def get_url_param(self, url, key):
         return dict(parse_qsl(urlparse(url).query))[key]

