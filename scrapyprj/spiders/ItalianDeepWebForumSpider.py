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


class ItalianDeepWebForumSpider(ForumSpiderV3):
    name = "italiandeepweb_forum"
    custom_settings = {
        'MAX_LOGIN_RETRY' : 10,
        'RANDOMIZE_DOWNLOAD_DELAY' : True,
        'HTTPERROR_ALLOW_ALL' : True,
        'RETRY_ENABLED' : True,
        'RETRY_TIMES' : 5
    }

    def __init__(self, *args, **kwargs):
        super(ItalianDeepWebForumSpider, self).__init__(*args, **kwargs)

        self.set_max_concurrent_request(1)      # Scrapy config
        self.set_download_delay(10)             # Scrapy config
        self.set_max_queue_transfer_chunk(1)    # Custom Queue system
        self.statsinterval = 60 				# Custom Queue system
        self.logintrial = 0						# Max login attempts.
        self.alt_hostnames = []					# Not in use.
        self.report_status = True				# Report 200's.
        self.loggedin = False					# Login flag. 

    def start_requests(self):
        yield self.make_request(url = 'http://kbyz2vu3fnv2di7l.onion', dont_filter=True)

    def make_request(self, reqtype='regular', **kwargs):
        if 'url' in kwargs:
            kwargs['url'] = self.make_url(kwargs['url'])
        # Handle the requests.
        # If you need to bypass DDoS protection, put it in here.
        if reqtype is 'dologin':
            req = self.craft_login_request_from_form(kwargs['response'])
            req.dont_filter = True
        elif reqtype is 'loginpage':
            req = Request(self.make_url('loginpage'), dont_filter = True)
        elif reqtype is 'regular':
            req = Request(kwargs['url'])
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
                yield self.make_request(reqtype='loginpage',response=response)
            else:
                # Try to yield informative error messages if we can't logon.
                if self.is_login_page(response) is True and self.login_failed(response) is True:
                    self.logger.info('Failed last login as %s. Trying again' % self.login['username'])
                # Allow the spider to fail if it can't log on.
                if self.logintrial > self.settings['MAX_LOGIN_RETRY']:
                    self.wait_for_input("Too many login failed")
                    self.logintrial = 0
                    return
                self.logger.info("Trying to login as %s." % self.login['username'])
                self.logintrial += 1
                yield self.make_request(reqtype='dologin', response=response)
        # Handle parsing.
        else:
            self.loggedin = True
            # We restore the missed request when protection kicked in
            if response.meta['reqtype'] == 'dologin':
                self.logger.info("Succesfully logged in as %s! " % (self.login['username']))

            if self.is_threadlisting(response) is True:
                parser = self.parse_threadlisting
            elif self.is_message(response) is True:
            	parser = self.parse_message
            elif self.is_user(response) is True:
            	parser = self.parse_user

            #Yield the appropriate parsing function.
            if parser is not None:
                for x in parser(response):
                    yield x
            else:
                self.logger.warning("Unknown page type at %s" % response.url)

    ########## PARSING FLAGS ##############
    def is_message(self, response):
        return '/showthread.php' in response.url

    def is_user(self, response):
        return '/member.php?action=profile&uid=' in response.url

    def is_threadlisting(self, response):
        return "/forumdisplay.php" in response.url

    ########## PARSING FUNCTIONS ##########
    def parse_user(self, response):
        # self.logger.info("Yielding profile from %s" % response.url)

        try:
            useritem                    = items.User()

            useritem['username']        = self.get_text(response.css("fieldset span.largetext span"))
            useritem['relativeurl']     = urlparse(response.url).path
            useritem['fullurl']         = response.url
            useritem['username_id']     = self.get_url_param(response.url, 'uid')

            trs = response.css("#content div.wrapper table.tborder tr")

            for tr in trs:
                if (len(tr.css('td')) == 2):
                    key = self.get_text(tr.css('td:first-child strong')).lower()
                    content = self.get_text(tr.xpath('.//td[last()]/text()').extract_first())

                    if key == 'joined:':
                        useritem['joined_on'] = self.parse_timestr(content)
                    elif key == 'last visit:':
                        useritem['last_active'] = self.parse_timestr(content)
                    elif key == 'total posts:':
                        match = re.match('(\d+\.?\d*)', content)
                        if match:
                            useritem['message_count'] = match.group(1)
                    elif key == 'total threads:':
                        match = re.match('(\d+\.?\d*)', content)
                        if match:
                            useritem['post_count'] = match.group(1)
                    elif key == 'reputation:':
                        useritem['reputation'] = self.get_text(tr.css('.reputation_positive'))
                    elif key == 'sex:':
                        useritem['gender'] = content
                    elif key in ['avatar', 'email:', 'private message:', 'bio:', 'time spent online:']:
                        pass
                    else:
                        self.logger.warning('New information found on user profile page : "%s"' % key)

            yield useritem

        except Exception as e:
            self.logger.warning("Cannot parse user item. %s" % e)
            pass


    def parse_message(self, response):
        # self.logger.info("Yielding messages from %s" % response.url)

        threadid    = self.get_url_param(response.url, 'tid')
        posts       = response.css("#posts .post")

        for post in posts:
            if not 'deleted_post_hidden' in post.xpath('@class').extract_first():
                try:
                    post_date           = self.parse_timestr(self.get_text(post.css('span.post_date::text')))
                    author_username     = self.get_text(post.css('.post_author .largetext a span'))
                    contenttext         = post.css('.post_body')
                    match               = re.match('post_(\d+)', post.xpath("@id").extract_first())

                    if match:
                        post_id = match.group(1)

                    messageitem                         = items.Message()

                    messageitem['author_username']      = author_username
                    messageitem['postid']               = post_id
                    messageitem['threadid']             = threadid
                    messageitem['posted_on']            = post_date
                    messageitem['contenttext']          = self.get_text(contenttext)
                    messageitem['contenthtml']          = contenttext.extract_first()

                    yield messageitem

                except Exception as e:
                    self.logger.warning("Cannot parse message item. %s" % e)
                    pass

    def parse_threadlisting(self, response):
        # self.logger.info("Yielding threads from %s" % response.url)
        
        threads = response.css("#content tr.inline_row")

        for thread in threads:
            try:
                threadlink          = thread.css("td:nth-child(3)").xpath(".//span[contains(@id, 'tid_')]/a")
                threadurl           = threadlink.xpath('@href').extract_first()
                lastpost_content    = self.get_text(thread.css("td:last-child span.lastpost"))
                match               = re.search("(.+)Ultimo", lastpost_content)

                if match:
                    last_post_time  = self.parse_timestr(match.group(1))

                threaditem                      = items.Thread()
                threaditem['threadid'] 		    = self.get_url_param(threadurl, 'tid')
                threaditem['title']			    = self.get_text(threadlink)
                threaditem['relativeurl']       = threadurl
                threaditem['fullurl']           = self.make_url(threadurl)
                threaditem['author_username']   = self.get_text(thread.css("td:nth-child(3) div.author a"))
                threaditem['last_update']       = last_post_time
                threaditem['replies']           = self.get_text(thread.css("td:nth-child(4) a"))
                threaditem['views']             = self.get_text(thread.css("td:nth-child(5)"))

                yield threaditem

            except Exception as e:
                self.logger.error("Cannot parse thread item : %s" % e)
                pass


    ############ LOGIN HANDLING ################
    def login_failed(self, response):
        return len(response.xpath('//div[@class="error"]')) > 0

    def islogged(self, response):
        if 'Log Out' in response.body:
            self.loggedin = True
            return True
        return False

    def is_login_page(self, response):
        return len(response.xpath('.//div[@class="wrapper"]//form[input[@value="do_login"]]')) > 0

    def craft_login_request_from_form(self, response):

        data = {
            'action':'do_login',
            'url':'http://kbyz2vu3fnv2di7l.onion/',
            'quick_login':'1',
            'quick_username':self.login['username'],
            'quick_password':self.login['password'],
            'submit':'Login',
        }         
        req = FormRequest.from_response(response, formdata=data, formnumber=2)
        req.dont_filter = True

        return req

    ########### MISCELLANEOUS ###################
    def parse_timestr(self, timestr):
        last_post_time = None
        if timestr == '(Hidden)':
            return last_post_time

        try:
            timestr = timestr.lower()
            timestr = timestr.replace('today', str(self.localnow().date()))
            timestr = timestr.replace('yesterday', str(self.localnow().date() - timedelta(days=1)))
            last_post_time = self.to_utc(dateutil.parser.parse(timestr))
        except:
            if timestr:
                self.logger.warning("Could not determine time from this string : '%s'. Ignoring" % timestr)
        return last_post_time
