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


class MercadoNegroForumSpider(ForumSpiderV3):
    name = "mercadonegro_forum"
    custom_settings = {
        'MAX_LOGIN_RETRY': 10,
        'RANDOMIZE_DOWNLOAD_DELAY': True,
        'HTTPERROR_ALLOW_ALL': True,
        'RETRY_ENABLED': True,
        'RETRY_TIMES': 5
    }

    def __init__(self, *args, **kwargs):
        super(self.__class__, self).__init__(*args, **kwargs)

        self.set_max_concurrent_request(1)      # Scrapy config
        self.set_download_delay(10)             # Scrapy config
        self.set_max_queue_transfer_chunk(1)    # Custom Queue system
        self.statsinterval = 60                 # Custom Queue system
        self.logintrial = 0                     # Max login attempts.
        self.alt_hostnames = []                 # Not in use.
        self.report_status = True               # Report 200's.
        self.loggedin = False                   # Login flag.

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
        elif reqtype is 'loginpage':
            req = Request(self.make_url('loginpage'), dont_filter=True, headers =self.tor_browser)
        elif reqtype is 'regular':
            req = Request(kwargs['url'], headers =self.tor_browser)
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
        # We tell the type so that we can redo it if login is required
        req.meta['reqtype'] = reqtype
        return req

    def parse_response(self, response):
        parser = None
        # Handle login status.
        if self.islogged(response) is False:
            self.loggedin = False
            if self.has_login_form(response) is False:
                # req_once_logged:
                # stores the request we will go to after logging in.
                req_once_logged = response.request
                yield self.make_request(reqtype='loginpage', response=response, req_once_logged=req_once_logged, priority = 10)
            else:
                req_once_logged = response.meta['req_once_logged'] if 'req_once_logged' in response.meta else response.request
                # Try to yield informative error messages if we can't logon.
                if self.has_login_form(response) is True and self.login_failed(response) is True:
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
            # Notify on succesful login and set parsing flag.
            # Parsing handlers.
            # A simple function designates whether a page should be parsed.
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
                    if response.url != self.make_url('index'):
                        self.logger.warning(
                            "Unknown page type at %s" % response.url)

    # ######### PARSING FLAGS ##############
    def is_message(self, response):
        if "viewtopic.php?" in response.url and "p=" not in response.url:
            return True

    def is_user(self, response):
        return 'memberlist.php?mode=viewprofile&u=' in response.url

    def is_threadlisting(self, response):
        return "viewforum.php?f=" in response.url

    # ######### PARSING FUNCTIONS ##########
    def parse_user(self, response):
        # self.logger.info("Yielding profile from %s" % response.url)
        user = items.User()
        user['relativeurl'] = urlparse(response.url).path
        user['fullurl'] = response.url

        dts = response.css("form#viewprofile dl dt")

        for dt in dts:
            key = self.get_text(dt).lower()
            value = dt.xpath('following-sibling::dd[1]')
            ddtext = self.get_text(value)

            if key == 'username:':
                user['username'] = ddtext
            elif key == 'groups:':
                user['group'] = value.css('*::text').extract_first()
            elif key == 'joined:':
                user['joined_on'] = self.parse_datetime(ddtext)
            elif key == 'last active:':
                user['last_post'] = self.parse_datetime(ddtext)
            elif key == 'total posts:':
                m = re.match(r"^(\d+).+", ddtext)
                if m:
                    user['post_count'] = m.group(1)
            elif key == 'pgpkey:':
                user['signature'] = ddtext

        yield user

    def parse_message(self, response):
        # try:
        #     threadid = self.get_url_param(response.url, 't')
        # except KeyError:
        #     # It shows one post in thread only, so ignore this page
        #     return
        try:
            threadid = self.get_url_param(response.url, 't')
            posts = response.css('div.postbody')
            for post in posts:
                    messageitem                     = items.Message()
                    messageitem['threadid']         = threadid
                    author                          = post.xpath('//a[starts-with(@class, "username")]/text()').extract_first()
                    messageitem['author_username']  = author
                    post_time                       = post.css('p.author *::text').extract()
                    messageitem['posted_on']        = dateutil.parser.parse(post_time[-1].strip())
                    post_link                       = post.css('p.author > a::attr(href)').extract_first()
                    messageitem['postid']           = self.get_url_param(post_link, 'p')
                    msg                             = post.css("div.content")
                    messageitem['contenttext']      = self.get_text(msg)
                    messageitem['contenthtml']      = self.get_text(msg.extract_first())

                    yield messageitem

        except Exception as e:
            self.logger.warning("Invalid thread page. %s" % e)
            inspect_response(response, self)

    def parse_threadlisting(self, response):
        # self.logger.info("Yielding threads from %s" % response.url)
        for line in response.css("ul.topiclist.topics li.row"):
            try:
                title = line.css("dt div.list-inner > a")
                # if not title:
                #     continue
                threaditem = items.Thread()
                threaditem['title']             = self.get_text(title)
                threaditem['relativeurl']       = title.xpath('@href').extract_first()
                threaditem['fullurl']           = self.make_url(threaditem['relativeurl'])
                threaditem['threadid']          = self.get_url_param(threaditem['fullurl'], 't')
                threaditem['author_username']   = line.css('div.topic-poster a::text').extract_first()
                threaditem['replies']           = line.css('dd.posts *::text').extract_first().strip()
                threaditem['views']             = line.css('dd.views *::text').extract_first().strip()
                yield threaditem
            except Exception as e:
                self.logger.warning("Invalid thread listing page. %s" % e)

    # ########### LOGIN HANDLING ################
    def login_failed(self, response):
        return len(response.css('form#login')) > 0 and \
                len(response.css('form#login .fields1 div.error')) > 0

    def islogged(self, response):
        return len(response.css('li#username_logged_in span.username')) > 0

    def has_login_form(self, response):
        return len(response.css('form input#username')) > 0 and len(response.css('form input#password')) > 0

    def craft_login_request_from_form(self, response):
        sid = response.xpath('//input[@name="sid"]/@value').extract_first()
        redirect = response.xpath('//input[@name="redirect"]/@value').extract_first()

        form_data = {
            'username': self.login['username'],
            'password': self.login['password'],
            'viewonline': '',
            'redirect': redirect,
            'login': 'Login',
        }
        if sid:
            form_data['sid'] = sid

        req = FormRequest(url=self.make_url('loginpage'), formdata=form_data, headers =self.tor_browser)
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
            if timestr:
                self.logger.warning("Could not determine time from this string: '%s'. Ignoring" % timestr)

        return last_post_time
