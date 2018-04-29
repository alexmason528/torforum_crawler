# -*- coding: utf-8 -*-

from __future__ import absolute_import

from datetime import timedelta
import re
from urlparse import urlparse

import dateutil.parser
from scrapy.http import FormRequest, Request
import scrapyprj.items.forum_items as items
from scrapyprj.spiders.ForumSpiderV3 import ForumSpiderV3


class ApollonMarketForumSpider(ForumSpiderV3):
    name = "apollonmarket_forum"
    custom_settings = {
        'MAX_LOGIN_RETRY': 10,
        'RANDOMIZE_DOWNLOAD_DELAY': True,
        'HTTPERROR_ALLOW_ALL': True,
        'RETRY_ENABLED': True,
        'RETRY_TIMES': 5
    }

    def __init__(self, *args, **kwargs):
        super(ApollonMarketForumSpider, self).__init__(*args, **kwargs)

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
            req = Request(self.make_url('loginpage'), dont_filter=True)
        elif reqtype is 'regular':
            req = Request(kwargs['url'])
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
            if self.is_login_page(response) is False:
                # req_once_logged:
                # stores the request we will go to after logging in.
                req_once_logged = response.request
                yield self.make_request(
                    reqtype='loginpage',
                    response=response,
                    req_once_logged=req_once_logged)
            else:
                req_once_logged = response.meta['req_once_logged'] \
                    if 'req_once_logged' in response.meta else response.request
                # Try to yield informative error messages if we can't logon.
                if self.is_login_page(response) is True \
                        and self.login_failed(response) is True:
                    self.logger.info(
                        'Failed last login as %s. Trying again. Error: %s' % (
                            self.login['username'],
                            self.get_text(
                                response.xpath('.//p[@class="error"]')
                                )
                            )
                        )
                # Allow the spider to fail if it can't log on.
                if self.logintrial > self.settings['MAX_LOGIN_RETRY']:
                    self.wait_for_input(
                        "Too many login failed", req_once_logged)
                    self.logintrial = 0
                    return
                self.logger.info("Trying to login as %s." %
                                 self.login['username'])
                self.logintrial += 1
                yield self.make_request(
                    reqtype='dologin',
                    response=response,
                    req_once_logged=req_once_logged
                    )
        # Handle parsing.
        else:
            # We restore the missed request when protection kicked in
            if response.meta['reqtype'] == 'dologin':
                self.logger.info(
                    "Succesfully logged in as %s! "
                    "Returning to stored request %s" % (
                        self.login['username'],
                        response.meta['req_once_logged']
                        )
                    )
                if response.meta['req_once_logged'] is None:
                    self.logger.warning(
                        "We are trying to yield a None."
                        " This should not happen."
                    )
                yield response.meta['req_once_logged']
                self.loggedin = True
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
        if "viewtopic.php?id=" in response.url:
            return True

    def is_user(self, response):
        if 'profile.php?id=' in response.url:
            return True

    def is_threadlisting(self, response):
        if "viewforum.php?id=" in response.url:
            return True

    # ######### PARSING FUNCTIONS ##########
    def parse_user(self, response):
        # self.logger.info("Yielding profile from %s" % response.url)
        user = items.User()
        user['relativeurl'] = urlparse(response.url).path
        user['fullurl'] = response.url

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
                m = re.match(r"^(\d+).+", ddtext)
                if m:
                    user['post_count'] = m.group(1)
            elif key == 'signature':
                user['signature'] = ddtext
            elif key == 'location':
                user['location'] = ddtext
            elif key == 'jabber':
                user['jabber'] = ddtext
            elif key == 'icq':
                user['icq'] = ddtext
            elif key == 'real name':
                user['realname'] = ddtext
            elif key == 'microsoft account':
                user['microsoft_account'] = ddtext
            elif key == 'yahoo! messenger':
                user['yahoo_messenger'] = ddtext
            elif key == 'website':
                user['website'] = ddtext
            elif key == 'email':
                user['email'] = ddtext
            elif key in ['avatar', 'pm']:
                pass
            else:
                self.logger.warning(
                    'New information found on use profile page : "%s"' % key)

            yield user

    def parse_message(self, response):
        # self.logger.info("Yielding messages from %s" % response.url)
        threadid = self.get_url_param(response.url, 'id')
        posts = response.css("#punviewtopic div.blockpost")
        for post in posts:
            try:
                messageitem = items.Message()
                posttime = self.parse_timestr(self.get_text(post.css("h2 a")))

                messageitem['author_username'] = self.get_text(
                    post.xpath(
                        ".//div[@class='postleft']/dl/dt/strong/a/text()"
                        ).extract_first())
                messageitem['postid'] = post.xpath("@id").extract_first()
                messageitem['threadid'] = threadid
                messageitem['posted_on'] = posttime

                msg = post.css("div.postmsg")
                messageitem['contenttext'] = self.get_text(msg)
                messageitem['contenthtml'] = self.get_text(msg.extract_first())

                yield messageitem
            except Exception as e:
                self.logger.warning("Invalid thread page. %s" % e)

    def parse_threadlisting(self, response):
        # self.logger.info("Yielding threads from %s" % response.url)
        for line in response.css("#punviewforum tbody tr"):
            threaditem = items.Thread()
            title = self.get_text(line.css("td:first-child a"))
            if title is '':
                continue
            last_post_time = self.parse_timestr(
                self.get_text(line.css("td:last-child a")))
            # First or None if empty
            threadlinkobj = next(
                iter(line.css("td:first-child a") or []), None)
            if threadlinkobj:
                threadlinkhref = threadlinkobj.xpath(
                    "@href").extract_first() if threadlinkobj else None
                threaditem['title'] = self.get_text(threadlinkobj)
                threaditem['relativeurl'] = threadlinkhref
                threaditem['fullurl'] = self.make_url(threadlinkhref)
                threaditem['threadid'] = self.get_url_param(
                    threaditem['fullurl'],
                    'id')
                byuser = self.get_text(line.css("td:first-child span.byuser"))
                m = re.match("by (.+)", byuser)  # regex
                if m:
                    threaditem['author_username'] = m.group(1)
                threaditem['last_update'] = last_post_time
                threaditem['replies'] = self.get_text(
                    line.css("td:nth-child(2)"))
                threaditem['views'] = self.get_text(
                    line.css("td:nth-child(3)"))

            yield threaditem

    # ########### LOGIN HANDLING ################
    def login_failed(self, response):
        if len(response.xpath('//ul[@class="error-list"]')) > 0:
            return True

    def islogged(self, response):
        logout_btn = response.xpath(
            '//li[@id="navlogout"]/a/text()').extract_first()
        if logout_btn is not None and logout_btn.lower() == "logout":
            return True
        else:
            return False

    def is_login_page(self, response):
        if len(response.css("form#login")) > 0:
            return True
        return False

    def craft_login_request_from_form(self, response):
        form_data = {
            'form_sent': '1',
            'redirect_url': 'http://apollionmy7q52qc.onion/index.php',
            'req_username': self.login['username'],
            'req_password': self.login['password'],
            'save_pass': '1',
            'login': 'Login',
        }
        req = FormRequest(url=self.make_url('dologin'), formdata=form_data)
        req.dont_filter = True
        return req

    # ########## MISCELLANEOUS ###################
    def parse_timestr(self, timestr):
        last_post_time = None
        try:
            timestr = timestr.lower()
            timestr = timestr.replace('today', str(self.localnow().date()))
            timestr = timestr.replace('yesterday', str(
                self.localnow().date() - timedelta(days=1)))
            last_post_time = self.to_utc(dateutil.parser.parse(timestr))
        except Exception as e:
            print(str(e))
            if timestr:
                self.logger.warning(
                    "Could not determine time from this string :"
                    " '%s'. Ignoring" % timestr)
        return last_post_time
