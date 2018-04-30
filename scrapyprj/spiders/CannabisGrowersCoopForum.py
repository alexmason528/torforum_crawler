# -*- coding: utf-8 -*-
from __future__ import absolute_import
from scrapy.http import FormRequest, Request
from scrapyprj.spiders.ForumSpiderV3 import ForumSpiderV3
import scrapyprj.items.forum_items as items
from datetime import timedelta
from urlparse import urlparse
import re
import dateutil
import time


class CannabisGrowersCoopForum(ForumSpiderV3):
    name = "cgmc_forum"

    custom_settings = {
        'MAX_LOGIN_RETRY': 10,
        'RANDOMIZE_DOWNLOAD_DELAY': True,
        'HTTPERROR_ALLOW_ALL': True,
        'RETRY_ENABLED': True,
        'RETRY_TIMES': 5
    }

    def __init__(self, *args, **kwargs):
        super(CannabisGrowersCoopForum, self).__init__(*args, **kwargs)

        self.set_max_concurrent_request(1)      # Scrapy config
        self.set_download_delay(15)             # Scrapy config
        self.set_max_queue_transfer_chunk(1)    # Custom Queue system
        self.statsinterval = 60                 # Custom Queue system
        self.logintrial = 0                     # Max login attempts.
        self.alt_hostnames = []                 # Not in use.
        self.report_status = True               # Report 200's.
        self.loggedin = False                   # Login flag.

    def start_requests(self):
        yield self.make_request(url="index", dont_filter=True, req_once_logged = self.make_url('index'))

    def make_request(self, reqtype='regular', **kwargs):
        if 'url' in kwargs and reqtype != 'captcha':
            kwargs['url'] = self.make_url(kwargs['url'])

        if reqtype is 'dologin':
            req = self.do_login(kwargs['response'])
        elif reqtype is 'regular':
            req = Request(kwargs['url'])
            req.meta["shared"] = True
        elif reqtype is 'captcha':
            captcha_full_url = self.spider_settings["endpoint1"] + \
                kwargs['url']
            req = Request(captcha_full_url)
        elif reqtype is 'loginpage':
            login_url = self.spider_settings["endpoint1"] + "login"
            req = Request(login_url, dont_filter=True)
        elif reqtype is 'forum_home':
            req = Request(self.spider_settings["endpoint"])

        # Some meta-keys that are shipped with the request.
        if 'relativeurl' in kwargs:
            req.meta['relativeurl'] = kwargs['relativeurl']
        if 'dont_filter' in kwargs:
            req.dont_filter = kwargs['dont_filter']
        if 'shared' in kwargs:
            req.meta['shared'] = kwargs['shared']
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
            req_once_logged = response.meta['req_once_logged'] \
                if 'req_once_logged' in response.meta else response.request

            if self.is_login_page(response) is False:
                # req_once_logged stores the request \
                # we will go to after logging in.
                yield self.make_request(
                    reqtype='loginpage',
                    response=response,
                    req_once_logged=req_once_logged)
            else:
                self.loggedin = False
                # Allow the spider to fail if it can't log on.
                if self.logintrial > self.settings['MAX_LOGIN_RETRY']:
                    self.wait_for_input(
                        "Too many login failed", req_once_logged)
                    self.logintrial = 0
                    return

                self.logger.info(
                    "Trying to login as %s." % self.login['username'])
                self.logintrial += 1
                yield self.make_request(
                    reqtype='dologin',
                    response=response,
                    req_once_logged=req_once_logged)
        # Handle parsing.
        else:
            # We restore the missed request when protection kicked in
            if response.meta['reqtype'] == 'dologin':
                if self.is_account(response) is True:
                    yield self.make_request(reqtype='forum_home')
                    return

                self.logger.info(
                    "Succesfully logged in as %s! "
                    "Returning to stored request %s" % (
                        self.login['username'],
                        response.meta['req_once_logged']
                        )
                    )
                if response.meta['req_once_logged'] is None:
                    self.logger.warning(
                        "We are trying to yield a None. "
                        "This should not happen."
                        )
                yield response.meta['req_once_logged']
                self.loggedin = True

            # Notify on succesful login and set parsing flag.
            else:
                if self.is_login_url(response) is True:
                    self.logger.info("Login URL was returned")
                    return
                elif self.is_user(response) is True:
                    parser = self.parse_user
                elif self.is_threadlisting(response) is True:
                    parser = self.parse_threadlisting
                elif self.is_message(response) is True:
                    parser = self.parse_message
                elif self.is_forum_domain(response) is False:
                    parser = None
                # Yield the appropriate parsing function.
                if parser is not None:
                    for x in parser(response):
                        yield x
                else:
                    self.logger.warning(
                        "Unknown page type at %s" % response.url)

    def is_forum_domain(self, response):
        if self.spider_settings["endpoint1"] in response.url:
            return False

        return True

    def is_account(self, response):
        if self.make_url('/account/') in response.url:
            return True

        return False

    def is_login_url(self, response):
        if "/login" in response.url:
            return True

        return False

    def islogged(self, response):
        logout_list = [
            self.get_text(response.css('header nav div a:last-child')),
        ]
        for item in logout_list:
            if "log out" in item.lower():
                return True

        return False

    def is_login_page(self, response):
        return response.css('form#login-form').extract_first() is not None

    def do_login(self, response):
        data = {
            'username': self.login['username'],
            'password': self.login['password'],
            'user_action': 'login',
            'return': 'login/'
        }
        req = FormRequest.from_response(
            response, formdata=data, formcss='form#login-form')
        req.dont_filter = True

        captcha_src = '/login/showCaptcha?' + str(int(time.time()))
        req.meta['captcha'] = {
            'request': self.make_request(
                url=captcha_src, dont_filter=True, reqtype='captcha'
                ),
            'name': 'captcha'
        }

        return req

    def is_threadlisting(self, response):
        return response.css(
            'ul.row.big-list.zebra'
            ).extract_first() is not None

    def is_message(self, response):
        if "/discussion/" in response.url:
            return True
        return False

    def is_user(self, response):
        if ("/u/" in response.url) or ("/v/" in response.url and "/comments/" not in response.url):
            return True
        return False

    def parse_user(self, response):
        user = items.User()
        user['relativeurl'] = self.get_relative_url(response.url)
        user['fullurl']     = response.url

        user['username']    = self.get_text(response.css("div.main-infos h2"))
        if user["username"] == "":
            self.logger.warning("Couldn't get username at %s. Field empty." % response.url)

        # Extract ratings.
        # If the user has no ratings, we will receive a "".
        rating_str = self.get_text(response.css("div.rating.stars"))
        if rating_str != "": 
            m = re.search(r"\[([\d\.]+)\]", rating_str, re.M | re.I)
            if m is not None:
                user["average_rating"] = m.group(1).strip()
            m = re.search(r"\(([\d]+)[\s]rating", rating_str, re.M | re.I)
            if m is not None:
                user["rating_count"] = m.group(1).strip()

        user["membergroup"] = self.get_text(response.css("div.main-infos p"))
        activity_list = response.css("div.corner ul.zebra.big-list li")

        for tr_item in activity_list:
            key = self.get_text(tr_item.css("div.main div span"))
            value = self.get_text(tr_item.css("div.aux div span"))

            if key == "":
                self.logger.warning("Key is ''. Value is %s at URL %s" % (value, response.url))
                #continue 

            if key == "Last Seen":
                user["last_activity"] = self.parse_timestr(value)
            elif key == "Forum Posts":
                user["post_count"] = value
            elif key == "Followers":
                user["followers"] = value
            else:
                self.logger.warning(
                    'New information found on use profile page: "{}", {}'
                    .format(key, response.url))
        yield user

    def parse_threadlisting(self, response):
        topics = response.css('ul.row.big-list.zebra > li')
        for topic in topics:
            threaditem = items.Thread()
            threaditem['title'] = self.get_text(
                topic.css("div.main > div > a"))

            href = topic.css("div.main > div > a::attr(href)").extract_first()
            threaditem['relativeurl'] = href
            if href != "":
                threaditem['fullurl'] = self.make_url(href)
            threadid = self.get_thread_id(href)
            threaditem['threadid'] = threadid
            threaditem['author_username'] = topic.css(
                "div.main > div > span a::text").extract_first()

            replies = self.get_text(
                topic.css("div.main > div > span strong:last-child"))
            if re.match(r'^\d+$', replies) is None:
                replies = 0
            threaditem['replies'] = replies
            yield threaditem

    def parse_message(self, response):
        posts = response.css('ul.row.list-posts > li')
        for post in posts:
            messageitem = items.Message()

            messageitem['author_username'] = self.get_text(
                post.css('.post-header a.poster'))
            messageitem['postid'] = self.get_post_id(
                post.css('span:first-child::attr(id)').extract_first())
            messageitem['threadid'] = self.get_thread_id(response.url)
            messageitem['posted_on'] = dateutil.parser.parse(self.get_text(
                post.css('.footer .cols-10 .col-4:first-child strong')))

            msg = post.css("div.content")
            messageitem['contenttext'] = self.get_text(msg)
            messageitem['contenthtml'] = self.get_text(msg.extract_first())
            yield messageitem

    def get_thread_id(self, uri):
        match = re.search(r'/discussion/(\d+)/', uri)
        if match:
            return match.group(1)
        match = re.search(r'/post/(\d+)/', uri)
        if match:
            return match.group(1)

        self.logger.warning("Couldn't get threadid at %s. Field empty." % uri)
        return None

    def get_post_id(self, uri):
        match = re.search(r'post-(\d+)', uri)
        if match:
            return match.group(1)
        match = re.search(r'comment-(\d+)', uri)
        if match:
            return match.group(1)
        self.logger.warning("Couldn't get postid at %s. Field empty." % uri)
        return None

    def parse_timestr(self, timestr):
        last_post_time = None
        try:
            timestr = timestr.lower()
            if "days ago" in timestr:
                v = re.search(
                    r"([\d]+)[\s]day",
                    timestr,
                    re.M | re.I | re.S
                    ).group(1).strip()
                timestr = str(self.localnow().date() - timedelta(days=int(v)))

            timestr = timestr.replace('today', str(self.localnow().date()))
            timestr = timestr.replace('today', str(self.localnow().date()))
            timestr = timestr.replace('yesterday', str(
                self.localnow().date() - timedelta(days=1)))
            last_post_time = self.to_utc(dateutil.parser.parse(timestr))
        except Exception:
            if timestr:
                self.logger.warning(
                    "Could not determine time from this string : "
                    "'%s'. Ignoring" % timestr)
        return last_post_time
