from __future__ import absolute_import
import scrapy
from scrapy.http import FormRequest,Request
from scrapy.shell import inspect_response
from scrapyprj.spiders.ForumSpider import ForumSpider
from scrapyprj.database.orm import *
import scrapyprj.database.forums.orm.models as models
import scrapyprj.items.forum_items as items
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

class OlympusMarketForumSpider(ForumSpider):
    name = "olympusmarket_forum"

    custom_settings = {
        'MAX_LOGIN_RETRY' : 10,
        'RESCHEDULE_RULES' : {
            'The post table and topic table seem to be out of sync' : 60
        },
        'HTTPERROR_ALLOW_ALL' : True,
        'RETRY_ENABLED' : True,
        'RETRY_TIMES' : 5       
    }

    def __init__(self, *args, **kwargs):
        super(self.__class__, self).__init__(*args, **kwargs)

        self.set_max_concurrent_request(2)      # Scrapy config
        self.set_download_delay(15)              # Scrapy config
        self.set_max_queue_transfer_chunk(1)    # Custom Queue system

        self.logintrial = 0
        self.parse_handlers = {
            'index'         : self.parse_index,
            'dologin'       : self.parse_index,
            'threadlisting' : self.parse_threadlisting,
            'thread'        : self.parse_thread,
            'userprofile'   : self.parse_userprofile,
        }

    def start_requests(self):
        yield self.make_request('index')

    def make_request(self, reqtype,  **kwargs):
        
        if 'url' in kwargs:
            kwargs['url'] = self.make_url(kwargs['url'])

        if reqtype == 'index':
            req = Request(self.make_url('index'), dont_filter=True)

        elif reqtype == 'dologin':
            req = self.send_login_request(kwargs['response'])
            req.dont_filter=True

        elif reqtype in ['threadlisting', 'thread', 'userprofile']:
            req = Request(self.make_url(kwargs['url']))
            req.meta['shared'] = True

            if 'relativeurl' in kwargs:
                req.meta['relativeurl'] = kwargs['relativeurl']
            if 'threadid' in kwargs:
                req.meta['threadid'] = kwargs['threadid']
            if 'username' in kwargs:
                req.meta['username'] = kwargs['username']


        else:
            raise Exception('Unsuported request type ' + reqtype)

        req.meta['reqtype'] = reqtype   # We tell the type so that we can redo it if login is required
        req.meta['proxy'] = self.proxy  #meta[proxy] is handled by scrapy.

        if 'req_once_logged' in kwargs:
            req.meta['req_once_logged'] = kwargs['req_once_logged']        

        return req
   
    def parse(self, response):
        if response.status in range(400, 600):
            self.logger.warning("%s response %s at URL %s" % (self.login['username'], response.status, response.url))
        else:
            self.logger.info("[Logged in = %s]: %s %s at %s URL: %s" % (self.islogged(response), self.login['username'], response.status, response.request.method, response.url))
        if not self.islogged(response):
            req_once_logged = response.meta['req_once_logged'] if 'req_once_logged'  in response.meta else response.request 
            
            if self.logintrial > self.settings['MAX_LOGIN_RETRY']:
                self.wait_for_input("Too many login failed", req_once_logged)
                self.logintrial = 0
                return

            self.logger.info("Trying to login as %s." % self.login['username'])
            self.logintrial += 1
            
            yield self.make_request(reqtype='dologin',response=response, req_once_logged=req_once_logged);  # We try to login and save the 
        else:
            self.logintrial = 0
            it = self.parse_handlers[response.meta['reqtype']].__call__(response)
            if it:
                for x in it:
                    if x != None:
                        yield x

    def parse_index(self, response):
        if 'req_once_logged' in response.meta:
            yield response.meta['req_once_logged']

        for line in response.css("#forums .category .nodeText"):
            link = line.css("h3.nodeTitle>a::attr(href)").extract_first()
            yield self.make_request('threadlisting', url=link)
    
    def parse_threadlisting(self, response):
        for line in response.css("div.discussionList li.discussionListItem"):
            threaditem                          = items.Thread()

            threadlink                          = line.css("div.main h3.title a::attr(href)").extract_first()
            threadid                            = self.read_threadid_from_url(threadlink)

            threaditem['title']                 =  self.get_text(line.css("div.main h3.title a"))
            threaditem['author_username']       = self.get_text(line.css("a.username"))
            threaditem['replies']               = self.get_text(line.css("div.stats .major dd"))
            threaditem['views']                 = self.get_text(line.css("div.stats .minor dd"))
            threaditem['last_update']           = self.parse_timestr(self.get_text(line.css("div.lastPost a.dateTime abbr")), response)
            threaditem['relativeurl']           = threadlink
            threaditem['fullurl']               = self.make_url(threadlink)
            threaditem['threadid']              = threadid

            yield threaditem
            yield self.make_request('thread', url=threadlink, threadid=threadid)

        for link in response.css(".PageNav nav a::attr(href)").extract():
            yield self.make_request('threadlisting', url=link)

    def parse_thread(self, response):
        threadid    =  response.meta['threadid']
        posts       = response.css("#messageList li.message")

        for post in posts:
            try:
                messageitem = items.Message()

                fullid                              = post.xpath("@id").extract_first()
                content                             = post.css("blockquote.messageText")
                userprofile_link                    = post.css("div.messageDetails a.username.author::attr(href)").extract_first()

                messageitem['author_username']      = self.get_text(post.css("div.messageDetails a.username.author"))
                messageitem['postid']               = re.match("post-(\d+)", fullid).group(1)
                messageitem['threadid']             = threadid
                messageitem['posted_on']            = self.parse_timestr(self.get_text(post.xpath(".//a[@class='datePermalink']")), response)
                messageitem['contenttext']          = self.get_text(content)
                messageitem['contenthtml']          = self.get_text(content.extract_first())

                yield messageitem

                yield self.make_request('userprofile', url = userprofile_link, relativeurl=userprofile_link, username=messageitem['author_username'])
            except Exception as e:
                self.logger.warning("Invalid thread page. %s" % e)

        for link in response.css(".PageNav nav a::attr(href)").extract():
            yield self.make_request('thread', url=link, threadid = response.meta['threadid'])


    def is_private_userprofile(self, response):
        error_msg = response.xpath('.//div[@class="errorOverlay"]/div/label/text()').extract_first()
        if error_msg is not None and "This member limits who may view their full profile" in error_msg:
            return True
        else:
            return False

    def is_unavailable_userprofile(self, response):
        error_msg = response.xpath('.//div[@class="errorOverlay"]/div/label/text()').extract_first()
        if error_msg is not None and "This user's profile is not available" in error_msg:
            return True
        else:
            return False

    def parse_userprofile(self, response):
        user = items.User()

        if self.is_private_userprofile(response) is True or self.is_unavailable_userprofile(response) is True:
            self.logger.warning("Encountered a limited/private/banned profile at %s. Basic info filled using meta-keys." % response.url)
            user['relativeurl']         = response.meta['relativeurl']
            user['fullurl']             = response.url
            user['username']            = response.meta['username']
            yield user
        else:
            user['relativeurl']         = response.meta['relativeurl']
            user['fullurl']             = response.url
            user['username']            = self.get_text(response.css("h1.username"))
            user['title']               = self.get_text(response.css("span.userTitle"))
            user['signature']           = self.get_text(response.css("div.signature"))

            dts = response.css("#content .mast dl dt")
            
            for dt in dts:
                key = self.get_text(dt).lower()
                ddtext = self.get_text(dt.xpath('following-sibling::dd[1]'))

                if key == 'joined:':
                    user['joined_on'] = self.parse_timestr(ddtext, response)
                elif key == 'messages:':
                    user['message_count'] = ddtext
                elif key == 'likes received:':
                    user['likes_received'] = ddtext
                elif key == 'home page:':
                    user['website'] = ddtext
                elif key == 'gender:':
                    user['gender'] = ddtext
                elif key == 'location:':
                    user['location'] = ddtext
                elif key == 'last activity:':
                    user['last_activity'] = ddtext
                elif key == 'email':
                    user['email'] = ddtext
                elif key == 'trophy points:':
                    user['trophy_points'] = ddtext
                elif key == 'birthday:':
                    user['birthday'] = ddtext
                elif key == 'occupation:':
                    user['occupation'] = ddtext
                elif key in ['avatar', 'pm']:
                    pass
                else:
                    self.logger.warning('New information found on use profile page: "%s"' % key)

            yield user

    def send_login_request(self, response):
        data = {
            'login' : self.login['username'],
            'password' : self.login['password']
        }

        req = FormRequest.from_response(response, formdata=data)

        return req

    def parse_timestr(self, timestr, response):
        post_time = None

        try:
            timestr     = timestr.lower()
            timestr     = timestr.replace('today', str(self.localnow().date()))
            timestr     = timestr.replace('yesterday', str(self.localnow().date() - timedelta(days=1)))
            post_time   = self.to_utc(dateutil.parser.parse(timestr))
        except:
            if timestr:
                self.logger.warning("Could not determine time from this string : '%s'. Ignoring" % timestr)
                self.logger.warning("At %s with HTML %s" % (response.url, response.body))

        return post_time

    def islogged(self, response):
        loggedin = False
        content = self.get_text(response.css("#AccountMenu"))

        if 'Log Out' in content:
            loggedin = True

        return loggedin

    def read_threadid_from_url(self, url):
        try:
            m   = re.match("threads/([^/]+)(/page-\d+)?", url)
            m2  = re.match("(.+\.)?(\d+)/?", m.group(1))
            return m2.group(2)
        except Exception as e:
            return None
