# -*- coding: utf-8 -*-

from __future__ import absolute_import

from datetime import timedelta
import re
from urlparse import urlparse

import dateutil.parser
from scrapy.http import FormRequest, Request
import scrapyprj.items.forum_items as items
from scrapyprj.spiders.ForumSpiderV3 import ForumSpiderV3
from scrapy.shell import inspect_response


class MajesticGardenForumSpider(ForumSpiderV3):
    name = "majesticgarden_forum"
    custom_settings = {
        'MAX_LOGIN_RETRY': 10,
        'RANDOMIZE_DOWNLOAD_DELAY': True,
        'HTTPERROR_ALLOW_ALL': True,
        'RETRY_ENABLED': True,
        'RETRY_TIMES': 5
    }

    def __init__(self, *args, **kwargs):
        super(MajesticGardenForumSpider, self).__init__(*args, **kwargs)

        self.set_max_concurrent_request(1)      # Scrapy config
        self.set_download_delay(10)             # Scrapy config
        self.set_max_queue_transfer_chunk(100)    # Custom Queue system
        self.statsinterval = 60                 # Custom Queue system
        self.logintrial = 0                     # Max login attempts.
        self.alt_hostnames = []                 # Not in use.
        self.report_status = False               # Report 200's.
        self.loggedin = False                   # Login flag.
        self.user_agent = {'User-Agent':' Mozilla/5.0 (Windows NT 6.1; rv:52.0) Gecko/20100101 Firefox/52.0'} # Base code assigns a random UA. Set it here in the        

    def start_requests(self):
        yield self.make_request(url='index', dont_filter=True)

    def make_request(self, reqtype='regular', **kwargs):
        if 'url' in kwargs:
            kwargs['url'] = self.make_url(kwargs['url'])
        # Handle the requests.
        # If you need to bypass DDoS protection, put it in here.
        if reqtype is 'dologin':
            req = self.craft_login_request_from_form(kwargs['response'])
            req.dont_filter = True
            req.priority    = 10
        elif reqtype is 'loginpage':
            req = Request(self.make_url('loginpage'), dont_filter=True, headers=self.user_agent, priority = 10)
        elif reqtype is 'regular':
            req = Request(kwargs['url'], headers=self.user_agent)
            # req.meta['shared'] = True # Ensures that requests are shared among spiders.
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
                yield self.make_request(reqtype='loginpage', response=response, req_once_logged=req_once_logged) 
            else:
                req_once_logged = response.meta['req_once_logged'] if 'req_once_logged' in response.meta else response.request
                # Try to yield informative error messages if we can't logon.
                if self.is_login_page(response) is True and self.login_failed(response) is True:
                    self.logger.info('Failed last login as %s. Trying again. Error: %s' % (self.login['username'], self.get_text(response.xpath('.//p[@class="error"]'))))
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
            self.loggedin = True
            # We restore the missed request when protection kicked in
            if response.meta['reqtype'] == 'dologin':
                self.logger.info("Succesfully logged in as %s! Returning to stored request %s" % (self.login['username'], response.meta['req_once_logged']))
                if response.meta['req_once_logged'] is None:
                    self.logger.warning("We are trying to yield a None. This should not happen.")
                yield response.meta['req_once_logged']
            # Parsing handlers.
            # A simple function designates whether a page should be parsed.
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
                    if response.url != self.make_url('index'):
                        self.logger.warning("Unknown page type at %s" % response.url)
    # ######### PARSING FLAGS ##############
    def is_message(self, response):
        if "index.php?topic=" in response.url:
            return True

    def is_threadlisting(self, response):
        if "index.php?board=" in response.url:
            return True

    # ######### PARSING FUNCTIONS ##########
    def parse_message(self, response):
        #self.logger.info("Yielding messages from %s" % response.url)
        threadid = self.get_url_param(response.url, 'topic').split(".")[0]
        posts = response.css("#forumposts div.windowbg") + response.css("#forumposts div.windowbg2")

        for post in posts:
            messageitem = items.Message()
            posttime = self.parse_timestr(re.search("«.*on:(.*?)»", self.get_text(post.css("div.keyinfo div.smalltext")), re.S | re.M).group(1).strip())

            author_username   = post.xpath(".//h4/a/text()").extract_first()
            if author_username is not None: # Verified posters.
                messageitem['author_username']        = author_username.strip()
            elif post.xpath(".//h4/text()").extract_first() is not None:
                messageitem['author_username']        = post.xpath(".//h4/text()").extract_first().strip()
            else:
                self.logger.warning('Unknown problem yielding user at URL %s' % response.url)
            messageitem['postid']            = post.css("div.post div.inner::attr(id)").extract_first().replace("msg_", "")
            messageitem['threadid']          = threadid
            messageitem['posted_on']         = posttime
            msg                              = post.css("div.post")
            messageitem['contenttext']       = self.get_text(msg)
            messageitem['contenthtml']       = self.get_text(msg.extract_first())
            yield messageitem

        for post in posts:
            useritem = items.User()
            username = post.xpath(".//h4/a/text()").extract_first()
            if username is not None: # Verified posters.
                useritem['username']        = username.strip()
                useritem["relativeurl"]     = self.get_relative_url(post.css(".poster h4 a::attr(href)").extract_first())
                useritem["fullurl"]         = self.make_url(post.css(".poster h4 a::attr(href)").extract_first())
            elif post.xpath(".//h4/text()").extract_first() is not None:
                useritem['username']        = post.xpath(".//h4/text()").extract_first().strip()
                useritem["relativeurl"]     = useritem['username']
                useritem["fullurl"]         = self.spider_settings['endpoint'] + useritem['username']
            else:
                self.logger.warning('Unknown problem yielding user at URL %s' % response.url)
            
            for li in post.xpath(".//ul/li"):
                 key = li.xpath(".//@class").extract_first()
                 keytext = li.xpath(".//text()").extract_first()
                 if key == "postgroup":
                     useritem['postgroup'] = keytext
                 elif key == "membergroup":
                     useritem['membergroup'] = keytext
                 elif key == 'karma':
                     useritem['karma'] = keytext.replace('Karma: ', '')
                 elif key == 'title':
                     useritem['title'] = keytext
                 elif key == 'stars':
                    useritem['stars'] = keytext
                 elif key == 'postcount':
                     useritem['post_count'] = keytext.replace('Posts: ', '')
                 elif key == 'custom':
                     awards = li.xpath(".//text()").extract()
                     useritem['awards'] = '|'.join(awards).replace('Awards: |', '')
                 elif key is None or key in ['blurb', 'avatar', 'profile', 'new_win', 'quote', 'quote_button']:
                     pass
                 else:
                     self.logger.warning("Unknown key in user profile '%s' with value '%s'" % (key, keytext))
            yield useritem
              


    def parse_threadlisting(self, response):
        for line in response.css("#messageindex table tbody tr"):
            threaditem                      = items.Thread()
            last_post_time                  = self.parse_timestr(self.get_text(line.css("td:last-child")).split("by")[0].strip())
            threadlinkobj                   = next(iter(line.css("td:nth-child(3) span a") or []), None)  # First or None if empty
            if threadlinkobj:
                threadlinkhref              = threadlinkobj.xpath("@href").extract_first() if threadlinkobj else None
                threaditem['title']         = self.get_text(threadlinkobj)
                threaditem['relativeurl']   = self.get_relative_url(threadlinkhref)
                threaditem['fullurl']       = self.make_url(threadlinkhref)
                threaditem['threadid']      = self.get_url_param(threaditem['fullurl'], 'topic').split(".")[0]
                byuser                      = self.get_text(line.xpath(".//div/p/a"))
                if byuser == '':
                    byuser = line.xpath(".//div/p[contains(text(), 'Started by')]/text()").extract_first().strip().replace("Started by ", "")
                threaditem['author_username'] = byuser
                threaditem['last_update']   = last_post_time
                reply_review                = self.get_text(line.css("td:nth-child(4)"))
                threaditem['replies']       = re.search(r"(\d+) Replies", reply_review, re.S | re.M).group(1)
                threaditem['views']         = re.search(r"(\d+) Views", reply_review, re.S | re.M).group(1)
                yield threaditem
            else:
                self.logger.warning('Couldn\'t yield thread. Please review: %s' % response.url)

    # ########### LOGIN HANDLING ################
    def login_failed(self, response):
        if len(response.xpath('.//p[@class="error"]')) > 0:
            return True

    def islogged(self, response):
        logout_btn = response.xpath('//li[@id="button_logout"]/a/span/text()').extract_first()
        if logout_btn is not None and logout_btn.lower() == "logout":
            return True
        else:
            return False

    def is_login_page(self, response):
        if len(response.css("form#frmLogin")) > 0:
            return True
        return False

    def craft_login_request_from_form(self, response):
        hidden_key = str(response.xpath(
            '//div[@class="roundframe"]/p[@class="centertext smalltext"]/following-sibling::input/@name').extract_first())
        hidden_val = str(response.xpath(
            '//div[@class="roundframe"]/p[@class="centertext smalltext"]/following-sibling::input/@value').extract_first())
        form_data = {
          'user': self.login['username'],
          'passwrd': self.login['password'],
          'cookieneverexp': 'on',
          hidden_key: hidden_val,
          'hash_passwrd': '',
        }
        req = FormRequest(url=self.make_url('dologin'), formdata=form_data, headers=self.user_agent)
        req.dont_filter = True
        return req

    # ########## MISCELLANEOUS ###################
    def parse_timestr(self, timestr):
        last_post_time = None
        try:
            timestr = timestr.lower()
            timestr = timestr.replace('today', str(self.localnow().date()))
            timestr = timestr.replace('yesterday', str(self.localnow().date() - timedelta(days=1)))
            last_post_time = self.to_utc(dateutil.parser.parse(timestr))
        except Exception as e:
            self.logger.warning("Error: %s at %s" % (str(e), response.url))  
            if timestr:
                self.logger.warning("Could not determine time from this string : '%s'. Ignoring" % timestr)
        return last_post_time
