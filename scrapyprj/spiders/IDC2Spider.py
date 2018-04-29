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
from dateutil.parser import parse
import dateutil.relativedelta as relativedelta

class IDC2Spider(ForumSpiderV3):
    name = "idc2_forum"  
    custom_settings = {
        'MAX_LOGIN_RETRY' : 10,
        'RANDOMIZE_DOWNLOAD_DELAY' : True,
        'HTTPERROR_ALLOW_ALL' : True,
        'RETRY_ENABLED' : True,
        'RETRY_TIMES' : 5
    }

    def __init__(self, *args, **kwargs):
        super(IDC2Spider, self).__init__(*args, **kwargs)

        self.set_max_concurrent_request(1)      # Scrapy config
        self.set_download_delay(10)             # Scrapy config
        self.set_max_queue_transfer_chunk(1)    # Custom Queue system
        self.statsinterval      = 60            # Custom Queue system
        self.logintrial         = 0             # Max login attempts.
        self.alt_hostnames      = []            # Not in use.
        self.report_status      = True          # Report 200's.
        self.loggedin           = False         # Login flag. 
        self.user_agent         = {'User-Agent':' Mozilla/5.0 (Windows NT 6.1; rv:52.0) Gecko/20100101 Firefox/52.0'} # Base code assigns a random UA. Set it here in the

    def start_requests(self):
        yield self.make_request(url = 'index', dont_filter=True)

    def make_request(self, reqtype='regular', **kwargs):
        if 'url' in kwargs:
            kwargs['url'] = self.make_url(kwargs['url'])
        # Handle the requests.
        if reqtype is 'dologin':
            req = self.craft_login_request_from_form(kwargs['response']) 
            req.dont_filter = True
        elif reqtype is 'loginpage':
            req = Request(self.make_url('loginpage'), dont_filter=True, headers=self.user_agent)
        elif reqtype is 'regular':
            req = Request(kwargs['url'], headers=self.user_agent)
            req.meta['shared'] = True 

        if 'relativeurl' in kwargs:
            req.meta['relativeurl'] = kwargs['relativeurl']
        if 'dont_filter' in kwargs:
            req.dont_filter = kwargs['dont_filter']
        if 'req_once_logged' in kwargs:
            req.meta['req_once_logged'] = kwargs['req_once_logged']  

        req.meta['proxy'] = self.proxy  
        req.meta['slot'] = self.proxy
        req.meta['reqtype'] = reqtype   
        return req

    def parse_response(self, response):
        parser = None
        # Handle login status.
        if self.islogged(response) is False:
            self.loggedin = False
            if self.is_login_page(response) is False:
                req_once_logged = response.meta['req_once_logged'] if 'req_once_logged' in response.meta else response.request
                yield self.make_request(reqtype='loginpage',response=response, req_once_logged=req_once_logged)                 
            else:
                req_once_logged = response.meta['req_once_logged'] if 'req_once_logged' in response.meta else response.request
                if self.is_login_page(response) is True and self.login_failed(response) is True:
                    self.logger.info('Failed last login as %s. Trying again. Error: %s' % (self.login['username'], self.get_text(response.xpath('.//div/ul[@class="error-list"]'))))
                if self.logintrial > self.settings['MAX_LOGIN_RETRY']:
                    self.wait_for_input("Too many login failed", req_once_logged)
                    self.logintrial = 0
                    return
                self.logger.info("Trying to login as %s." % self.login['username'])
                self.logintrial += 1
                yield self.make_request(reqtype='dologin', response=response, req_once_logged=req_once_logged)
        # Handle parsing.
        else:
            self.loggedin = True
            if response.meta['reqtype'] == 'dologin':
                self.logger.info("Succesfully logged in as %s! Returning to stored request %s" % (self.login['username'], response.meta['req_once_logged']))
                if response.meta['req_once_logged'] is None:
                    self.logger.warning("We are trying to yield a None. This should not happen.")
                yield response.meta['req_once_logged']
            if self.is_threadlisting(response) is True:
                parser = self.parse_threadlisting
            elif self.is_parse_thread(response) is True:
                parser = self.parse_thread
            if self.is_restricted_page(response) is True:
                self.logger.warning("Encountered a restricted page at %s. Consider checking it out using a non-operating profile (mrmiyagi pass0000) or adding it to the exclude-list." % response.url)    
            if parser is not None:
                for x in parser(response):
                    yield x
            else:
                self.logger.info("Unknown page type at %s" % response.url)

    ########## PARSING FLAGS ##############
    def is_parse_thread(self, response):
        if "showthread.php?tid=" in response.url:
            return True

    def is_threadlisting(self, response):
        if "forumdisplay.php?fid=" in response.url:
            return True

    ########## PARSING FUNCTIONS ##########
    def parse_thread(self, response):
        posts = response.xpath('.//div[@class="post "]')
        for post in posts:
            messageitem                     = items.Message()
            #if posts.xpath('.//span[contains(text(), "Unregistered")]'):
            #    continue
            #else:
            #    self.logger.warning("Unhandled error. Couldn't parse posts at URL %s" % response.url)
            # Yield message.
            guest_user   = len(post.xpath('.//span[contains(text(), "Unregistered")]')) > 0
            special_user = guest_user is True and post.xpath('.//div[@class="author_information"]/strong/span/a[contains(@href, "member")]//text()').extract_first() is not None


            if guest_user is False or special_user is True:
                messageitem['author_username']  = post.xpath('.//div[@class="author_information"]//a[contains(@href, "member")]//text()').extract_first()
                if messageitem['author_username'] is None:
                    messageitem['author_username'] = post.xpath('.//div[@class="author_information"]/strong/span/a[contains(@href, "member")]//text()').extract_first()
                messageitem['postid']           = post.xpath('@id').extract_first().lstrip('post_')
                messageitem['threadid']         = re.search('tid\=([0-9]+)', response.url).group(1)
                msg                             = post.xpath('.//div[contains(@class, "post_body")]')
                messageitem['contenttext']      = self.get_text(msg)
                messageitem['contenthtml']      = self.get_text(msg.extract_first())
                # Post date handling
                posted_on                       = post.xpath('.//span[@class="post_date"]/text()').extract_first()
                messageitem['posted_on']        = self.parse_date_idc(posted_on)
            else:
                messageitem['author_username']  = post.xpath('div/div/strong/span/text()').extract_first()
                messageitem['postid']           = post.xpath('@id').extract_first().lstrip('post_')
                messageitem['threadid']         = re.search('tid\=([0-9]+)', response.url).group(1)
                msg                             = post.xpath('.//div[contains(@class, "post_body")]')
                messageitem['contenttext']      = self.get_text(msg)
                messageitem['contenthtml']      = self.get_text(msg.extract_first())
                # Post date handling
                posted_on                       = post.xpath('.//span[@class="post_date"]/text()').extract_first()
                messageitem['posted_on']        = self.parse_date_idc(posted_on)                
            if messageitem['author_username'] is None:
                inspect_response(response, self)

            yield messageitem

            # Yield user.
            useritem = items.User()
            if guest_user is False or special_user is True:
                useritem['username']        = messageitem['author_username']
                useritem['fullurl']         = post.xpath('.//div[@class="author_information"]//span[@class="largetext"]/a/@href').extract_first()
                useritem['relativeurl']     = useritem['fullurl'].split('.onion')[1]
                useritem['title']           = post.xpath('.//div[@class="author_information"]//span[@class="smalltext"]/text()[1]').extract_first().strip()
                message_count               = post.xpath('.//div[@class="author_statistics"]/text()[2]').extract_first()
                useritem['message_count']   = int(re.sub('[^0-9]', '', message_count))
                post_count                  = post.xpath('.//div[@class="author_statistics"]/text()[3]').extract_first()
                useritem['post_count']      = int(re.sub('[^0-9]', '', post_count))
                useritem['joined_on']       = post.xpath('.//div[@class="author_statistics"]/text()[4]').extract_first().replace("Registrato: ")
                useritem['reputation']      = post.xpath('.//strong[contains(@class, "reputation")]/text()').extract_first()
                useritem['post_count']      = int(re.sub('[^0-9]', '', post_count))
                useritem['username_id']     = re.search('([0-9]+)', useritem['relativeurl']).group(1)
                useritem['membergroup']     = post.xpath('.//img[not(@class="buddy_status")]/@title').extract_first()                
            else:
                # Unregistered users have no message count, join date, post count, reputation, id..
                useritem['username']        = messageitem['author_username']
                useritem['fullurl']         = self.spider_settings['endpoint'] + "/" + useritem['username']
                useritem['relativeurl']     = useritem['username']
                useritem['title']           = post.xpath('.//div[@class="author_information"]//span[@class="smalltext"]/text()[1]').extract_first().strip()

            yield useritem

    def parse_threadlisting(self, response):
        topics = response.xpath('.//tr[@class="inline_row"]')
        for topic in topics:
            threaditem                    = items.Thread()
            threaditem['title']           =  topic.xpath('.//span[contains(@id, "tid")]/a/text()').extract_first()
            threaditem['relativeurl']     = topic.xpath('.//span[contains(@id, "tid")]/a/@href').extract_first()
            threaditem['fullurl']         = self.make_url(threaditem['relativeurl'])
            threaditem['threadid']        = re.search('([0-9]+)', threaditem['relativeurl']).group(1)
            threaditem['author_username'] = topic.xpath('.//div[contains(@class, "author")]/a/text()').extract_first()
            threaditem['replies']         = re.sub('[^0-9]', '', topic.xpath('.//td[4]/a/text()').extract_first())
            threaditem['views']           = re.sub('[^0-9]', '', topic.xpath('.//td[5]/text()').extract_first())
            # Last update handling
            lastupdate = topic.xpath('.//span[contains(@class, "lastpost")]/text()[1]').extract_first()
            threaditem['last_update'] = self.parse_date_idc(lastupdate)
                       
            yield threaditem

    ############ LOGIN HANDLING ################
    def login_failed(self, response):
        if len(response.xpath('//div[@class="error"]')) > 0:
            return True

    def islogged(self, response):
        if 'Logout' in response.body:
            return True
        return False

    def is_login_page(self, response):
        if len(response.xpath('.//div[@class="wrapper"]//form[input[@value="do_login"]]')) > 0:
            return True
        return False

    def craft_login_request_from_form(self, response):
        captcha_src = response.css("form#login img::attr(src)").extract_first()
        if captcha_src:
            imagehash = response.xpath('//input[@id="imagehash"]/@value').extract_first()
            data = {
                'username':self.login['username'],
                'password':self.login['password'],
                'remember':'yes',
                'imagehash':imagehash,
                'submit':'Login',
                'action':'do_login',
            }
            req.meta['captcha'] = {        # CaptchaMiddleware will take care of that.
                'request' : self.make_request(url=captcha_src, dont_filter = True, priority = 10),
                'name' : 'imagestring',    # Preprocess image to extract what's within the rectangle
                'preprocess' : 'DreamMarketRectangleCropper'
                }
        else:
            data = {
                'username' : self.login['username'],
                'password' : self.login['password']
            }            
        req = FormRequest.from_response(response, formdata=data, headers=self.user_agent)
        req.dont_filter = True

        return req

    def is_restricted_page(self, response):
        restricted = response.xpath('.//div[@class="wrapper"]').xpath(".//td[@class='trow1']/text()").extract_first()
        if restricted is not None and "Non hai i permessi per accedere a questa pagina." in restricted:
            return True
        else:
            return False 

    ########### MISCELLANEOUS ###################
    def parse_date_idc(self, date):
        if re.search(r'oggi', date): # 'Today, HH:MM PM/AM'
            time = dateutil.parser.parse(re.sub(r'oggi, ', '', date))
            return datetime.now() + relativedelta(hour=time.hour, minute=time.minute, second=0)
        elif re.search(r'ieri', date): # 'Yesterday, HH:MM PM/AM'
            time = dateutil.parser.parse(re.sub(r'ieri, ', '', date))
            return datetime.now() + relativedelta(days=-1, hour=time.hour, minute=time.minute, second=0)
        elif re.search(r'ore fa', date): # 'HH hours ago'
            hours_ago = int(re.search('([0-9]+)', date).group(1))
            return datetime.now() + relativedelta(hours=-hours_ago, second=0)
        elif re.search(r'minuti fa', date): # 'HH minutes ago'
            minutes_ago = int(re.search('([0-9]+)', date).group(1))
            return datetime.now() + relativedelta(minutes=-minutes_ago, second=0)
        else:
            return dateutil.parser.parse(date)