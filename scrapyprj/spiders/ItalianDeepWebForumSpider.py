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
            req_once_logged = response.meta['req_once_logged'] if 'req_once_logged'  in response.meta else response.request
            if self.is_login_page(response) is False:
                # req_once_logged stores the request we will go to after logging in.
                yield self.make_request(reqtype='loginpage',response=response, req_once_logged=req_once_logged)
            else:
                # Try to yield informative error messages if we can't logon.
                if self.is_login_page(response) is True and self.login_failed(response) is True:
                    self.logger.info('Failed last login as %s. Trying again' % self.login['username'])
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
            # else:
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
                self.logger.info("Unknown page type at %s" % response.url)

    ########## PARSING FLAGS ##############
    def is_message(self, response):
        if '/showthread.php?tid=' in response.url:
            return True

    def is_user(self, response):
        if '/member.php?action=profile&uid=' in response.url:
            return True

    def is_threadlisting(self, response):
        if "/forumdisplay.php?fid=" in response.url:
            return True
    ########## PARSING FUNCTIONS ##########
    def parse_user(self, response):
        self.logger.info("Yielding profile from %s" % response.url)
        user = items.User()
        user['relativeurl'] = urlparse(response.url).path
        user['fullurl'] = response.url
        user['username'] = self.get_text(response.css("fieldset table span.largetext em"))
        
        trs = response.css("table.tborder tbody tr")

        for tr in trs:
            if (len(tr.css('td')) == 2):
                key = self.get_text(tr.css('td:first-child strong'))
                content = self.get_text(tr.css('td:last-child'))

                if key == 'Iscritto dal:':
                    user['joined_on'] = self.parse_timestr(content)
                elif key == 'Ultima visita:':
                    user['last_activity'] = self.parse_timestr(content)
                elif key == 'Reputazione:':
                    user['reputation'] = self.get_text(tr.css('td:last-child .reputation_neutral'))
                elif key in ['avatar', 'pm']:
                    pass
                else:
                    self.logger.warning('New information found on use profile page : "%s"' % key)

        yield user

    def parse_message(self, response):
        self.logger.info("Yielding messages from %s" % response.url)
        threadid =  self.get_url_param(response.url, 'tid')
        posts = response.css("#post_container div.posts div.post")
        for post in posts:
            try:
                messageitem = items.Message()
                posttime = self.parse_timestr(self.get_text(post.css("span.post_date")))

                messageitem['author_username'] = self.get_text(post.css(".post_author .author_information span.largettext em").extract_first())
                messageitem['postid'] = post.xpath("@id").extract_first()
                messageitem['threadid'] = threadid
                messageitem['posted_on'] = posttime

                msg = post.css("div.post_body")
                messageitem['contenttext'] = self.get_text(msg)
                messageitem['contenthtml'] = self.get_text(msg.extract_first())

                yield messageitem
            except Exception as e:
                self.logger.warning("Invalid thread page. %s" % e)

    def parse_threadlisting(self, response):
        self.logger.info("Yielding threads from %s" % response.url)
        for line in response.css("#content tbody tr.inline_row"):
            threaditem = items.Thread()
            threadlinkobj = line.css("td:nth-child(2) span.subject_new a") if len(line.css("td:nth-child(2) span.subject_new")) > 0 else line.css("td:nth-child(2) span.subject_old a")
            last_post_time = self.parse_timestr(self.get_text(line.css("td:last-child span.lastpost")))
            if threadlinkobj:
                threadlinkhref = threadlinkobj.xpath("@href").extract_first() if threadlinkobj else None
                threaditem['title'] = self.get_text(threadlinkobj)
                threaditem['relativeurl'] = threadlinkhref
                threaditem['fullurl']   = self.make_url(threadlinkhref)             
                threaditem['threadid'] = self.get_url_param(threaditem['fullurl'], 'tid')
                threaditem['author_username'] = self.get_text(line.css("td:nth-child(2) div.author a"))
                threaditem['last_update'] = last_post_time
                threaditem['replies']   = self.get_text(line.css("td:nth-child(4) a"))
                threaditem['views']     = self.get_text(line.css("td:nth-child(5)"))

            self.logger.warning(threaditem)

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
        try:
            timestr = timestr.lower()
            timestr = timestr.replace('today', str(self.localnow().date()))
            timestr = timestr.replace('yesterday', str(self.localnow().date() - timedelta(days=1)))
            last_post_time = self.to_utc(dateutil.parser.parse(timestr))
        except:
            if timestr:
                self.logger.warning("Could not determine time from this string : '%s'. Ignoring" % timestr)
        return last_post_time
