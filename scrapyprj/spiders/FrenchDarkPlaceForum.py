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

class FrenchDarkPlaceForum(ForumSpiderV3):
    name = "frenchdarkplace_forum"
  
    custom_settings = {
        'MAX_LOGIN_RETRY'           : 10,
        'RANDOMIZE_DOWNLOAD_DELAY'  : True,
        'HTTPERROR_ALLOW_ALL'       : True,
        'RETRY_ENABLED'             : True,
        'RETRY_TIMES'               : 5
    }

    def __init__(self, *args, **kwargs):
        super(FrenchDarkPlaceForum, self).__init__(*args, **kwargs)

        self.set_max_concurrent_request(1)      # Scrapy config
        self.set_download_delay(10)             # Scrapy config
        self.set_max_queue_transfer_chunk(16)   # Custom Queue system
        self.statsinterval = 60                 # Custom Queue system
        self.logintrial = 0                     # Max login attempts.
        self.alt_hostnames = []                 # Not in use.
        self.report_status = True               # Report 200's.
        self.loggedin = False                   # Login flag. 
        self.user_agent = {'User-Agent':' Mozilla/5.0 (Windows NT 6.1; rv:52.0) Gecko/20100101 Firefox/52.0'} # Base code assigns a random UA. Set it here in the

    def start_requests(self):
        yield self.make_request(url = 'index', dont_filter=True)

    def make_request(self, reqtype='regular', **kwargs):
        if 'url' in kwargs:
            kwargs['url'] = self.make_url(kwargs['url'])

        # Handle the requests.
        # If you need to bypass DDoS protection, put it in here.
        if reqtype is 'dologin':
            req = self.craft_login_request_from_form(kwargs['response']) 
        elif reqtype is 'loginpage':
            req = Request(self.make_url('loginpage'), dont_filter=True, headers=self.user_agent)
        elif reqtype is 'regular':
            req = Request(kwargs['url'], headers=self.user_agent)
            req.meta['shared'] = True # Ensures that requests are shared among spiders.

        # Some meta-keys that are shipped with the request.
        if 'relativeurl' in kwargs:
            req.meta['relativeurl'] = kwargs['relativeurl']
        if 'dont_filter' in kwargs:
            req.dont_filter = kwargs['dont_filter']
        if 'req_once_logged' in kwargs:
            req.meta['req_once_logged'] = kwargs['req_once_logged']

        req.meta['proxy']    = self.proxy  
        req.meta['slot']     = self.proxy
        req.meta['reqtype']  = reqtype   # We tell the type so that we can redo it if login is required
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
                if self.login_failed(response) is True:
                    self.logger.info('Failed last login as %s. Trying again.' % self.login['username'])

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
            self.loggedin = True
            if response.meta['reqtype'] == 'dologin':
                self.logger.info("Succesfully logged in as %s! Returning to stored request %s" % (self.login['username'], response.meta['req_once_logged']))
                if response.meta['req_once_logged'] is None:
                    self.logger.warning("We are trying to yield a None. This should not happen.")
                yield response.meta['req_once_logged']                
            else:
                if self.is_threadlisting(response) is True:
                    parser = self.parse_threadlisting
                elif self.is_message(response) is True:
                    parser = self.parse_message
                # Yield the appropriate parsing function.
                if parser is not None:
                    for x in parser(response):
                        yield x
                else:
                    self.logger.info("Unknown page type at %s" % response.url)

    ########## PARSING FLAGS ##############
    def is_message(self, response):
        return "viewtopic.php?id=" in response.url

    def is_threadlisting(self, response):
        return "viewforum.php?id=" in response.url
            
    ########## PARSING FUNCTIONS ##########            
    def parse_message(self, response):
        # self.logger.info("Yielding messages from %s" % response.url)
        threadid    = self.get_url_param(response.url, 'id')
        posts       = response.css("#brdmain .blockpost")

        for post in posts:
            messageitem                         = items.Message()
            messageitem['contenthtml']          = post.xpath(".//div[@class='postmsg']").extract_first()
            messageitem['contenttext']          = self.get_text(post.xpath(".//div[@class='postmsg']"))
            messageitem['postid']               = self.get_url_param(post.css("h2 span a::attr(href)").extract_first(), 'pid')
            messageitem['threadid']             = threadid
            messageitem['author_username']      = self.get_text(post.css(".postleft dl dt strong span"))

            # messageitem['posted_on']            = self.get_text(post.css("h2 span a"))

            yield messageitem


            useritem                = items.User()
            useritem['username']    = self.get_text(post.css(".postleft dl dt strong span"))

            # self.logger.info("Yielding profile for %s" % useritem['username'])

            member_group = post.css(".postleft dd.usertitle")
            if len(member_group) > 0:
                useritem['membergroup'] = self.get_text(member_group)

            website = post.css(".postleft dd.usercontacts span.website a::attr(href)")
            if len(website) > 0:
                useritem['website'] = self.get_text(website)

            attributes = post.css(".postleft dd")

            for attribute in attributes:
                if not attribute.css("span::attr(class)"):
                    content     = self.get_text(attribute.css("span"))
                    match       = re.search('(.+): (.+)', content)

                    if match:
                        key = match.group(1)
                        value = match.group(2)

                        if 'From' in key or 'Lieu' in key:
                            useritem['location'] = value
                        elif 'Posts' in key or 'Messages' in key:
                            useritem['post_count'] = value
                        elif 'Registered' in key or 'Inscription' in key:
                            useritem['joined_on'] = self.parse_timestr(value)
                            #pass
                        else:
                            self.logger.warning('New information found : %s' % key)

            yield useritem

    def parse_threadlisting(self, response):
        # self.logger.info("Yielding threads from %s" % response.url)

        threads = response.css('#vf table tbody tr')
        for thread in threads:
            try:
                threadlink          = thread.css('td:first-child a')
                threadurl           = thread.css('td:first-child a::attr(href)').extract_first()
                thread_last_update  = self.get_text(thread.css('td:last-child a'))

                threaditem                          = items.Thread()
                threaditem['threadid']              = self.get_url_param(threadurl, 'id')
                threaditem['title']                 = self.get_text(threadlink)
                threaditem['author_username']       = self.get_text(thread.css('td:first-child span.byuser span'))
                threaditem['last_update']           = self.parse_timestr(thread_last_update)
                threaditem['relativeurl']           = threadurl
                threaditem['fullurl']               = self.make_url(threadurl)
                threaditem['replies']               = self.get_text(thread.css('td:nth-child(2)'))
                threaditem['views']                 = self.get_text(thread.css('td:nth-child(3)'))

                yield threaditem

            except Exception as e:
                self.logger.error("Cannot parse thread item : %s" % e)
                pass

    ############ LOGIN HANDLING ################
    def login_failed(self, response):
        return 'login.php?action=in' in response.url and len(response.css('#brdmain div.inbox')) > 0

    def islogged(self, response):
        if len(response.css('#brdmenu li#navlogout')) > 0:
            self.loggedin = True
            return True
        return False

    def is_login_page(self, response):
        return len(response.css("form#login")) > 0

    def craft_login_request_from_form(self, response):
        data = {
            'req_username' : self.login['username'],
            'req_password' : self.login['password'],
        }

        req = FormRequest.from_response(response, formdata=data, dont_filter=True, headers=self.user_agent)

        return req

    ########### MISCELLANEOUS ###################
    def parse_timestr(self, timestr):
        last_post_time = None
        try:
            timestr         = timestr.lower()
            timestr         = timestr.replace('today', str(self.localnow().date()))
            timestr         = timestr.replace('yesterday', str(self.localnow().date() - timedelta(days=1)))
            last_post_time  = self.to_utc(dateutil.parser.parse(timestr))
        except:
            if timestr:
                self.logger.warning("Could not determine time from this string : '%s'. Ignoring" % timestr)
        return last_post_time
