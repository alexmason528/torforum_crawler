from __future__ import absolute_import
import scrapy
from scrapy.http import FormRequest,Request
from scrapy.shell import inspect_response
from scrapyprj.spiders.ForumSpiderV3 import ForumSpiderV3
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
from random import randint

class SilkRoadSpider(ForumSpiderV3):
    name = "silkroad_forum"  
    custom_settings = {
        'MAX_LOGIN_RETRY' : 10,
        'RANDOMIZE_DOWNLOAD_DELAY' : True,
        'HTTPERROR_ALLOW_ALL' : True,
        'RETRY_ENABLED' : True,
        'RETRY_TIMES' : 5
    }

    headers = {
        'User-Agent':' Mozilla/5.0 (Windows NT 6.1; rv:52.0) Gecko/20100101 Firefox/52.0',
        'Accept':' text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language':' en-US,en;q=0.5',
        'Accept-Encoding':' gzip, deflate',
        'Connection':' keep-alive',
        'Upgrade-Insecure-Requests':'1',
    }

    def __init__(self, *args, **kwargs):
        super(SilkRoadSpider, self).__init__(*args, **kwargs)

        self.set_max_concurrent_request(1)      # Scrapy config
        self.set_download_delay(10)             # Scrapy config
        self.set_max_queue_transfer_chunk(16)   # Custom Queue system
        self.statsinterval = 60                 # Custom Queue system
        self.logintrial = 0                     # Max login attempts.
        self.alt_hostnames = []                 # Not in use.
        self.report_status = True               # Report 200's.
        self.loggedin = False                   # Login flag. 

    def start_requests(self):
        yield self.make_request(url = 'index', dont_filter=True)

    def make_request(self, reqtype='regular', **kwargs):
        if 'url' in kwargs:
            kwargs['url'] = self.make_url(kwargs['url'])
        # Handle the requests.
        # If you need to bypass DDoS protection, put it in here.
        if reqtype is 'dologin':
            req = self.craft_login_request_from_form(kwargs['response']) 
            req.dont_filter = True
        elif reqtype is 'loginpage':
            req = Request(self.make_url('loginpage'), headers=self.headers, dont_filter=True)
        elif reqtype is 'regular':
            req = Request(kwargs['url'], headers=self.headers)
            req.meta['shared'] = True # Ensures that requests are shared among spiders.

        # Some meta-keys that are shipped with the request.
        if 'relativeurl' in kwargs:
            req.meta['relativeurl'] = kwargs['relativeurl']
        if 'dont_filter' in kwargs:
            req.dont_filter = kwargs['dont_filter']
        if 'req_once_logged' in kwargs:
            req.meta['req_once_logged'] = kwargs['req_once_logged']  
        req.meta['proxy'] = self.proxy  
        req.meta['slot'] = self.proxy
        req.meta['reqtype'] = reqtype   # We tell the type so that we can redo it if login is required
        return req

    def parse_response(self, response):
        parser = None
        # Handle login status.

        if self.islogged(response) is False:
            self.loggedin = False
            if self.is_login_page(response) is False:
                # req_once_logged stores the request we will go to after logging in.
                req_once_logged = response.request
                yield self.make_request(reqtype='loginpage',response=response, req_once_logged=req_once_logged) 
            else:
                req_once_logged = response.meta['req_once_logged'] if 'req_once_logged'  in response.meta else response.request
                # Try to yield informative error messages if we can't logon.
                if self.is_login_page(response) is True and self.login_failed(response) is True:
                    self.logger.info('Failed last login as %s. Trying again. Error: %s' % (self.login['username'], self.get_text(response.xpath('.//div/ul[@class="error-list"]'))))
                # Allow the spider to fail if it can't log on.
                if self.logintrial > self.settings['MAX_LOGIN_RETRY']:
                    self.wait_for_input("Too many login failed", req_once_logged)
                    self.logintrial = 0
                    return
                self.logger.info("Trying to login as %s." % self.login['username'])
                self.logintrial += 1
                yield self.make_request(reqtype='dologin', response=response, req_once_logged=req_once_logged)
        # Handle parsing.
        else:
            # We restore the missed request when protection kicked in
            if response.meta['reqtype'] == 'dologin':
                self.logger.info("Succesfully logged in as %s! Returning to stored request %s" % (self.login['username'], response.meta['req_once_logged']))
                if response.meta['req_once_logged'] is None:
                    self.logger.warning("We are trying to yield a None. This should not happen.")
                yield response.meta['req_once_logged']
                self.loggedin = True
            else:
                if self.is_threadlisting(response) is True:
                    parser = self.parse_threadlisting
                elif self.is_message(response) is True:
                    parser = self.parse_message
                elif self.is_user(response) is True:
                    parser = self.parse_user
                # Yield the appropriate parsing function.
                if parser is not None:
                    for x in parser(response):
                        yield x
                else:
                    self.logger.info("Unknown page type at %s" % response.url)
    ########## PARSING FLAGS ##############
    def is_message(self, response):
        if "viewtopic.php?" in response.url:
            return True

    def is_user(self, response):
        if 'memberlist.php?mode=viewprofile' in response.url:
            return True

    def is_threadlisting(self, response):
        if "viewforum.php?" in response.url:
            return True
        
    ########## PARSING FUNCTIONS ##########
    def parse_user(self, response):
        #self.logger.info("Yielding profile from %s" % response.url)
        if response.xpath('.//div[@class="inner"]/p/text()').extract_first() and "The requested user does not exist." in response.xpath('.//div[@class="inner"]/p/text()').extract_first():
            self.logger.warning('User profile not available. Likely deleted: "%s"' % response.url)
            return
        else:
            user = items.User()
            user['relativeurl'] = response.url.replace('http://satri4bb5r56y253.onion/.', '')
            user['fullurl'] = response.url
            dts = response.css("#viewprofile dl dt")

            for dt in dts:
                key = self.get_text(dt).lower()
                ddtext = self.get_text(dt.xpath('following-sibling::dd[1]'))

                if key == 'username:':
                    user['username'] = ddtext
                elif key == 'total posts:':
                    user['message_count'] = ddtext.split('|')[0].strip()
                elif key == 'joined:':
                    user['joined_on'] = self.parse_timestr(ddtext)
                elif key == 'last active:':
                    user['last_activity'] = self.parse_timestr(ddtext)
                # There are additional items
                elif key == 'rank:':
                    pass
                    # user['rank'] = ddtext  
                elif key == 'groups:':
                    user['membergroup'] = ddtext
                elif key == 'most active forum:':
                    pass
                    # user['most active forum'] = ddtext  
                elif key == 'most active topic:':
                    pass
                    # user['most active topic'] = ddtext
                elif key == '':
                    pass
                else:
                    self.logger.warning('New information found on use profile page : "%s"' % key)

            yield user

    def parse_message(self, response):
        #self.logger.info("Yielding messages from %s" % response.url)
        if response.xpath('.//div[@class="inner"]/p/text()').extract_first() and "The requested topic does not exist." in response.xpath('.//div[@class="inner"]/p/text()').extract_first():
            self.logger.warning('Post not available. Likely deleted: "%s"' % response.url)
            return
        else:
            m = re.search("t=(\d+)", response.url)
            if m:      
                threadid = m.group(1).strip()
            else:
                # If the page has a p= and no t= in the URL, we need to fetch the threadid inside the post.
                threadid = response.xpath('.//h2[@class="topic-title"]/a/@href').extract_first()
                if threadid:
                    threadid = re.search('t=(\d+)', threadid).group(1)
                else:
                    self.logger.warning("Couldn't identify the threadid at URL %s" % response.url)
                #m = re.search("p=(\d+)", response.url)
                #if m:      
                #    threadid = m.group(1).strip()
            posts = response.xpath('//div[contains(@class, "post has-profile")]')
            for post in posts:
                try:
                    messageitem = items.Message()
                    posttime = post.xpath('.//span[@class="responsive-hide"]/following-sibling::text()').extract_first()
                    messageitem['author_username'] = post.xpath('.//a[contains(@class, "username")]/text()').extract_first()
                    messageitem['postid'] = post.xpath('@id').extract_first()
                    messageitem['threadid'] = threadid
                    if posttime:
                        messageitem['posted_on'] = self.parse_timestr(posttime)

                    msg = post.xpath('.//div[@class="content"]')
                    messageitem['contenttext'] = self.get_text(msg)
                    messageitem['contenthtml'] = self.get_text(msg.extract_first())

                    yield messageitem
                except Exception as e:
                    self.logger.warning("Invalid thread page. %s" % e)

    def parse_threadlisting(self, response):
        self.logger.info("Yielding threads from %s" % response.url)

        for line in response.xpath('//ul[@class="topiclist topics"]/li'):
            threaditem = items.Thread()
            title =  line.xpath('.//a[@class="topictitle"]/text()').extract_first()
            last_post_time = self.parse_timestr(line.xpath('.//a[@title="Go to last post"]/text()').extract_first())
            threaditem['title'] = line.xpath('.//a[@class="topictitle"]/text()').extract_first()
            threaditem['relativeurl'] = line.xpath('.//a[@class="topictitle"]/@href').extract_first()
            threaditem['fullurl']   = self.make_url(threaditem['relativeurl'])             
            threaditem['threadid'] = threaditem['relativeurl'].split('&t=')[-1]
            threaditem['author_username'] = line.xpath('.//a[contains(@class, "username")]/text()').extract_first()
            threaditem['last_update'] = last_post_time
            threaditem['replies']   = line.xpath('.//dd[@class="posts"]/text()').extract_first().strip()
            threaditem['views']     = line.xpath('.//dd[@class="views"]/text()').extract_first().strip()

            yield threaditem

    ############ LOGIN HANDLING ################
    def login_failed(self, response):
        if len(response.xpath('.//div/ul[@class="error-list"]')) > 0:
            return True

    def islogged(self, response):        
        if "Logout" in response.xpath('.//ul[@class="dropdown-contents"]/li/a/span/text()').extract():
            return True
        return False

    def is_login_page(self, response):
        if len(response.css("form#login")) > 0:
            return True
        return False

    def craft_login_request_from_form(self, response):
        sid = response.xpath('//input[@name="sid"]/@value').extract_first()
        data = {
            'username':self.login['username'],
            'password':self.login['password'],
            'autologin':'on',
            'viewonline':'on',
            'redirect':'./ucp.php?mode:login',
            'sid':sid,
            'redirect':'index.php',
            'login':'Login',
        }

        req = FormRequest.from_response(response, formid='login', formdata=data)

        req.dont_filter = True
        return req

    ########### MISCELLANEOUS ###################
    def parse_timestr(self, timestr):
        last_post_time = None
        if timestr == "-":
            return last_post_time
        timestr = timestr.lower()
        try:
            if ("minutes ago" in timestr) or ("minute ago" in timestr):
                if "less" in timestr:
                    timestr = str(self.localnow().date())
                    last_post_time = self.to_utc(dateutil.parser.parse(timestr))                    
                else:
                    minutes = timestr.split(" ")[0]
                    timestr = str(self.localnow().date() - timedelta(minutes=int(minutes)))
                    last_post_time = self.to_utc(dateutil.parser.parse(timestr))
            else:
                timestr = timestr.replace('today', str(self.localnow().date()))
                timestr = timestr.replace('yesterday', str(self.localnow().date() - timedelta(days=1)))
                last_post_time = self.to_utc(dateutil.parser.parse(timestr))
        except:
            if timestr:
                self.logger.warning("Could not determine time from this string : '%s'. Ignoring" % timestr)
        return last_post_time