# -*- coding: utf-8 -*-
from __future__ import absolute_import
from scrapy.http import FormRequest, Request
from scrapyprj.spiders.ForumSpiderV3 import ForumSpiderV3
import scrapyprj.items.forum_items as items
from datetime import timedelta
from urlparse import urlparse
import re
import dateutil


class BerlusconiMarketForumSpider(ForumSpiderV3):
    name = "berlusconimarket_forum"
    custom_settings = {
        'MAX_LOGIN_RETRY': 10,
        'RANDOMIZE_DOWNLOAD_DELAY': True,
        'HTTPERROR_ALLOW_ALL': True,
        'RETRY_ENABLED': True,
        'RETRY_TIMES': 5
    }

    def __init__(self, *args, **kwargs):
        super(BerlusconiMarketForumSpider, self).__init__(*args, **kwargs)

        self.set_max_concurrent_request(2)      # Scrapy config
        self.set_download_delay(10)             # Scrapy config
        self.set_max_queue_transfer_chunk(5)   # Custom Queue system
        self.statsinterval = 60                 # Custom Queue system
        self.logintrial = 0                     # Max login attempts.
        self.alt_hostnames = []                 # Not in use.
        self.report_status = True               # Report 200's.
        self.loggedin = False                   # Login flag.
        self.user_agent = {'User-Agent':' Mozilla/5.0 (Windows NT 6.1; rv:52.0) Gecko/20100101 Firefox/52.0'} # Base code assigns a random UA. Set it here in the

    def start_requests(self):
        yield self.make_request(url="index", dont_filter=True, req_once_logged=self.make_url('homepage'), shared=False)

    def make_request(self, reqtype='regular', **kwargs):
        if 'url' in kwargs:
            kwargs['url'] = self.make_url(kwargs['url'])

        # Handle the requests.
        # If you need to bypass DDoS protection, put it in here.

        if reqtype is 'dologin':
            req = self.craft_login_request_from_form(kwargs['response'])
            req.meta['shared'] = False
            req.priority       = 10
        elif reqtype is 'loginpage':
            req = Request(self.make_url('loginpage'), dont_filter=True)
            req.meta['shared'] = False
            req.priority       = 15
            req.dont_filter    = True
        elif reqtype is 'regular':
            req = Request(kwargs['url'], headers=self.user_agent)
            req.meta['shared'] = True

        # Some meta-keys that are shipped with the request.
        if 'relativeurl' in kwargs:
            req.meta['relativeurl'] = kwargs['relativeurl']
        if 'dont_filter' in kwargs:
            req.dont_filter = kwargs['dont_filter']
        if 'req_once_logged' in kwargs:
            req.meta['req_once_logged'] = kwargs['req_once_logged']
        if 'shared' in kwargs:
            req.meta['shared'] = kwargs['shared']
        
        req.meta['proxy'] = self.proxy
        req.meta['slot'] = self.proxy
        req.meta['reqtype'] = reqtype   # We tell the type so that we can redo it if login is required
        return req

    def parse_response(self, response):
        parser = None
        # Handle login status.
        if self.islogged(response) is False:
            self.loggedin = False
            req_once_logged = response.meta['req_once_logged'] if 'req_once_logged' in response.meta else response.request
            if self.is_login_page(response) is False:
                self.logger.info("%s, not logged in. Going to login page" % (self.login['username']))
                yield self.make_request(reqtype='loginpage', response=response, req_once_logged=req_once_logged)
            elif self.is_login_page(response) is True:
                self.logger.info("Trying to login as %s." % self.login['username'])
                self.logintrial += 1
                # Allow the spider to fail if it can't log on.
                if self.logintrial > self.settings['MAX_LOGIN_RETRY']:
                    self.wait_for_input("Too many login failed", req_once_logged)
                    self.logintrial = 0
                    return
                yield self.make_request(reqtype='dologin', response=response, req_once_logged=req_once_logged)
            else:
                self.logger.warning("This error should not appear.")
        # Handle parsing.
        elif self.islogged(response) is True:
            # We restore the missed request when protection kicked in
            if response.meta['reqtype'] == 'dologin' and self.loggedin is False:
                self.logger.info("Succesfully logged in as %s! Returning to stored request %s" % (self.login['username'], response.meta['req_once_logged']))
                if response.meta['req_once_logged'] is None:
                    self.logger.warning("We are trying to yield a None. This should not happen.")
                self.loggedin = True
                yield response.meta['req_once_logged']
            # Notify on succesful login and set parsing flag.
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
                    self.logger.warning("Unknown page type at %s" % response.url)
        else:
            self.logger.warning("Error inside logged-in block. Should not happen.")

    def is_message(self, response):
        if "showthread.php?" in response.url:
            return True

    def is_user(self, response):
        if 'member.php?' in response.url:
            return True

    def is_threadlisting(self, response):
        if "forumdisplay.php?" in response.url:
            return True

    # ######### PARSING FUNCTIONS ##########
    def parse_user(self, response):
        #self.logger.info("Yielding profile from %s" % response.url)
        user = items.User()
        user['relativeurl'] = urlparse(response.url).path + "?" + urlparse(response.url).query
        user['fullurl'] = response.url

        user_info_td = response.xpath("//fieldset[not(@id)]/table//td[1]")

        user['username'] = self.get_text(user_info_td.xpath(".//span[@class='largetext']/strong"))

        if user["username"] == "":
            self.logger.warning("Could not get username. %s %s" %(response.url, response.body))
            #return

        user["rating_count"] = len(user_info_td.xpath(".//span[@class='smalltext']/img"))

        text_html = self.get_text(user_info_td.xpath(".//span[@class='smalltext']"))
        try:
            user['membergroup'] = re.search(r"\((.*)\)Registration Date", text_html, re.M | re.I | re.S).group(1).strip()
        except Exception as e:
            self.logger.warning("membergroup error %s with value %s" % (response.url, e))

        birthday_str = ""
        try:
            birthday_str = re.search("Date of Birth:(.*)Local Time", text_html, re.M | re.I | re.S).group(1).strip()
        except Exception as e:
            self.logger.warning("birthday error %s value %s" % (response.url, e))

        if birthday_str == "Not Specified":
            birthday_str = ""

        user['birthday'] = birthday_str

        forum_info_list = response.xpath("//fieldset[not(@id)]/following-sibling::table[1]//table[1]//tr")

        for tr_item in forum_info_list:
            key = self.get_text(tr_item.xpath("td[not(@class='thead')]/strong"))
            value = self.get_text(tr_item.xpath("td[2]"))

            if key == "":
                continue

            if key == "Last Visit:":
                user["last_activity"] = value.split("(")[0]
            elif key == "Total Posts:":
                user["post_count"] = value.split(" (")[0].strip()
                try:
                    user["post_per_day"] = re.search(r"\((.*)posts per day", value, re.M | re.I | re.S).group(1).strip()
                except Exception as e:
                    self.logger.warning("Couldn't get posts peer day. Please verify at %s" % response.url)

            elif key == "Joined:":
                user['joined_on'] = value
            elif "Reputation:" in key:
                self.get_text(tr_item.xpath(".//strong[contains(@class, 'reputation_')]"))
                user['reputation'] = self.get_text(tr_item.xpath(".//strong[contains(@class, 'reputation_')]"))
            elif "Sex:" == key:
                if value != "Undisclosed":
                    user["gender"] = value
            elif "Location:" == key:
                    user["location"] = value
            elif "Bio" in key:
                pass
            elif "Total Threads" in key:
                pass
            elif "Public PGP Key:" in key:
                pass
            elif "Time Spent Online" in key:
                pass
            elif "Warning Level:" in key:
                pass
            else:
                self.logger.warning('New information found on use profile page: "{}", {}'.format(key, response.url))
        yield user

    def parse_message(self, response):
        #self.logger.info("Yielding messages from %s" % response.url)
        threadid = ""
        try:
            threadid = self.get_url_param(response.url, 'tid')
        except Exception as e:
            self.logger.warning("Couldn't get threadid at %s with error %s" %(response.url, e))
            return

        posts = response.css("#posts div.post")
        for post in posts:
            try:
                messageitem = items.Message()
                posttime = self.get_text(post.css("div.post_head span.post_date")).split("(")[0]
                messageitem['author_username'] = self.get_text(post.xpath(".//div[@class='author_information']//span[@class='largetext']/a"))
                messageitem['postid'] = post.xpath("@id").extract_first(" ").replace("post_", "").strip()
                messageitem['threadid'] = threadid
                messageitem['posted_on'] = self.parse_timestr(posttime)
                msg = post.css("div.post_body")
                messageitem['contenttext'] = self.get_text(msg)
                messageitem['contenthtml'] = self.get_text(msg.extract_first())

                yield messageitem
            except Exception as e:
                self.logger.warning("Invalid thread page. %s" % e)

    def parse_threadlisting(self, response):
        #self.logger.info("Yielding threads from %s" % response.url)
        for line in response.css("div.wrapper table tr.inline_row"):
            threaditem = items.Thread()

            threaditem['title'] = self.get_text(line.xpath("td[3]/div/span/span/a"))
            if threaditem['title'] == "":
                continue

            threaditem['replies'] = self.get_text(line.css("td:nth-child(4)"))
            threaditem['views'] = self.get_text(line.css("td:nth-child(5)"))
            threaditem['relativeurl'] = line.xpath("td[3]/div/span/span/a/@href").extract_first()
            threaditem['fullurl'] = self.make_url(threaditem['relativeurl'])
            last_post_time = self.get_text(line.css("td:nth-child(6) span.lastpost"))
            try:
                threaditem['last_update'] = self.parse_timestr(re.search("(.*)last ", last_post_time, re.M|re.I|re.S).group(1).strip())
            except Exception as e:
                self.logger.warning("last_update %s error %s" % (response.url, e))

            try:
                threaditem['author_username'] = re.search("post:(.*)", last_post_time, re.M | re.I | re.S).group(1).strip()
            except Exception as e:
                self.logger.warning("author_username %s error value %s" % (response.url, e))

            threaditem['threadid'] = self.get_url_param(threaditem['fullurl'], 'tid')

            yield threaditem

    # ########### LOGIN HANDLING ################
    def login_failed(self, response):
        pass

    def islogged(self, response):
        if len(response.xpath('//a[@class="logout"]')) > 0:
            return True
        return False

    def is_login_page(self, response):
        return response.url.endswith("/member.php?action=login")

    def craft_login_request_from_form(self, response):
        response_url = response.url
        if response.url == self.spider_settings["endpoint"]:
            response_url = self.make_url("homepage")

        formdata = [
          ('action', 'do_login'),
          ('url', response_url),
          ('quick_login', '1'),
          ('quick_username', self.login['username']),
          ('quick_password', self.login['password']),
          ('submit', 'Login'),
        ]

        req = FormRequest(url=self.make_url('dologin'), dont_filter=True, formdata=formdata, headers=self.user_agent)
        return req

    # ########## MISCELLANEOUS ###################
    def parse_timestr(self, timestr):
        last_post_time = None
        try:
            timestr = timestr.lower()
            if "ago" in timestr:
                timestr = str(self.localnow().date())

            timestr = timestr.replace('today', str(self.localnow().date()))
            timestr = timestr.replace('today', str(self.localnow().date()))
            timestr = timestr.replace('yesterday', str(self.localnow().date() - timedelta(days=1)))
            last_post_time = self.to_utc(dateutil.parser.parse(timestr))
        except Exception as e:
            if timestr:
                self.logger.warning("Could not determine time from this string : '%s'. Ignoring" % timestr)
        return last_post_time
