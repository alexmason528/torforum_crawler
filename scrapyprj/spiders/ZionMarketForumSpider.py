from datetime import datetime, timedelta
from dateutil import parser
import re
from urlparse import urlparse
from scrapy.http import FormRequest, Request
from scrapyprj.spiders.ForumSpider import ForumSpider
import scrapyprj.items.forum_items as items
from scrapy.shell import inspect_response
import time


class ZionMarketForumSpider(ForumSpider):
    name = "zionmarket_forum"

    custom_settings = {
        'MAX_LOGIN_RETRY' : 10,
        'HTTPERROR_ALLOW_ALL' : True,
        'RETRY_ENABLED' : True,
        'RETRY_TIMES' : 5
    }

    def __init__(self, *args, **kwargs):
        super(self.__class__, self).__init__(*args, **kwargs)

        self.logintrial = 0
        self.set_max_concurrent_request(3)      # Scrapy config
        self.set_download_delay(15)             # Scrapy config
        self.set_max_queue_transfer_chunk(1)    # Custom Queue system
        self.user_agent = {'User-Agent':' Mozilla/5.0 (Windows NT 6.1; rv:52.0) Gecko/20100101 Firefox/52.0'} # Base code assigns a random UA. Set it here in the


        self.parse_handlers = {
            'index'         : self.parse_index,
            'threadlisting' : self.parse_thread_listing,
            'thread'        : self.parse_thread
        }

    def start_requests(self):
        yield self.make_request('index')

    def make_request(self, reqtype, **kwargs):
        if 'url' in kwargs:
            kwargs['url'] = self.make_url(kwargs['url'])

        if 'redirect_from' in kwargs:
            req = Request(kwargs['url'], headers=self.user_agent)
            req.meta['redirect_from'] = kwargs['redirect_from']
            req.dont_filter = True
        elif reqtype == 'index':
            req = Request(self.make_url('index'), headers=self.user_agent)
            req.dont_filter = True
        elif reqtype == 'ddos_protection':
            req = self.create_request_from_ddos_protection(kwargs['response'])
            req.meta['ddos_protection'] = True
            req.dont_filter = True
        elif reqtype == 'captcha':
            req = Request(kwargs['url'], headers=self.user_agent)
            req.dont_filter = True
        elif reqtype == 'dologin':
            req = self.create_request_from_login_page(kwargs['response'])
            req.dont_filter = True
        elif reqtype in ['threadlisting', 'thread']:
            req = Request(kwargs['url'], headers=self.user_agent)
            req.dont_filter = False
            req.meta['shared'] = True
        if reqtype == 'threadlisting':
            req.priority = 10

        req.meta['reqtype'] = reqtype # We tell the type so that we can redo it if login is required
        req.meta['proxy'] = self.proxy # meta[proxy] is handled by scrapy.

        if 'priority' in kwargs:
            req.priority = kwargs['priority']

        if 'req_once_logged' in kwargs:
            req.meta['req_once_logged'] = kwargs['req_once_logged']

        if 'shared' in kwargs:
            req.meta['shared'] = kwargs['shared']
        elif 'shared' not in kwargs:
            req.meta['shared'] = False


        return req

    def parse(self, response):
        if response.status in range(400, 600):
            self.logger.warning("%s response %s at URL %s" %
                                (self.login['username'], response.status, response.url))
        else:
            self.logger.info("[Logged in = %s | Shared = %s]: %s %s at %s URL: %s" % (
                self.loggedin(response), response.meta['shared'], self.login['username'],
                response.status, response.request.method, response.url))

        if self.require_redirect(response):
            redirect = self.get_redirect_link(response)
            req_once_logged = response.meta['req_once_logged'] \
                            if 'req_once_logged' in response.meta else None
            self.logger.debug('Redirect to ' + redirect)

            yield self.make_request(response.meta['reqtype'], req_once_logged=req_once_logged,
                                    url=redirect, redirect_from=response.request)

            return

        if 'redirect_from' in response.request.meta:
            response.request = response.request.meta['redirect_from']

        if self.loggedin(response) is False:
            if self.is_ddos_protection_form(response):
                self.logger.warning('Encountered a DDOS protection page as %s' %
                                    self.login['username'])
                if self.logintrial > self.settings['MAX_LOGIN_RETRY']:
                    req_once_logged = response.meta['req_once_logged'] \
                                    if 'req_once_logged' in response.meta else None
                    self.logintrial = 0
                    self.wait_for_input("Can't bypass DDOS Protection", req_once_logged)
                    return

                self.logger.info("Trying to overcome DDOS protection")
                self.logintrial += 1

                req_once_logged = response.request
                if 'req_once_logged' in response.meta:
                    req_once_logged = response.meta['req_once_logged']

                yield self.make_request('ddos_protection', req_once_logged=req_once_logged,
                                        response=response, priority=10)

            elif self.has_login_form(response):
                self.logger.debug('Encountered a login page.')
                if self.logintrial > self.settings['MAX_LOGIN_RETRY']:
                    req_once_logged = response.meta['req_once_logged'] \
                                    if 'req_once_logged' in response.meta else None
                    self.wait_for_input("Too many login failed", req_once_logged)
                    self.logintrial = 0
                    return

                self.logger.info("Trying to login as %s." % self.login['username'])
                self.logintrial += 1

                if 'req_once_logged' in response.meta:
                    req_once_logged = response.meta['req_once_logged']

                yield self.make_request('dologin', req_once_logged=req_once_logged,
                                        response=response, priority=10)

            else:
                self.logger.warning('Something went wrong. See the exception and investigate %s.' \
                                    ' Dumping html: %s' % (response.url, response.body))
                raise Exception("Not implemented yet, figure what to do here !")

        else:
            self.logintrial = 0

            # We restore the missed request when protection kicked in
            if response.meta['reqtype'] == 'dologin':
                self.logger.warning("Login Success! Going to %s" % response.meta['req_once_logged'])
                if response.meta['req_once_logged'] is None:
                    self.logger.warning("We are trying to yield a None. This should not happen.")
                yield response.meta['req_once_logged']

            # Normal parsing
            else:
                handlers = self.parse_handlers[response.meta['reqtype']].__call__(response)
                if handlers:
                    for handler in handlers:
                        if handler:
                            yield handler

    def parse_index(self, response):
        category_links = response.css('.table.forum > tbody > tr > td:nth-child(2) > a::attr(href)')
        for category_link in category_links.extract():
            yield self.make_request(reqtype='threadlisting', url=category_link, shared=True)

    def parse_thread_listing(self, response):
        for line in response.css('.table.forum > tbody > tr'):
            try:
                cells = line.css('td')
                if len(cells) != 4:
                    continue

                thread_link = cells[1].css('h4 div a::attr(href)').extract_first()
                if not thread_link:
                    continue

                threaditem = items.Thread()
                threaditem['title'] = cells[1].css('h4 div a::text').extract_first()
                threaditem['relativeurl'] = thread_link
                threaditem['fullurl'] = self.make_url(thread_link)
                threaditem['threadid'] = self.get_id_from_url(thread_link)

                author = cells[1].css('h4 div small a')
                if author:
                    threaditem['author_username'] = author.css('::text').extract_first().strip()
                else:
                    byuser = cells[1].xpath('.//h4/div/small//text()').extract()
                    byuser = ''.join(byuser)
                    if byuser:
                        matches = re.search(" ago by (.+)", byuser) # regex
                        if matches:
                            threaditem['author_username'] = matches.group(1).strip()
                # Cannot get last update time exactly, that's because the update time
                # doesn't follow time format, it's something like "XX days ago".
                moment_time_value = cells[3].css('small::text').extract()[-1]
                threaditem['last_update'] = self.parse_timestr(moment_time_value)
                threaditem['replies'] = cells[2].css('::text').extract_first()

                yield threaditem

                yield self.make_request('thread', url=thread_link, shared=True)

            except Exception as ex:
                self.logger.warning("Error in retrieving theads. %s at URL %s" % (ex, response.url))

        for link in response.css("a.paginate[rel='next']::attr(href)").extract():
            yield self.make_request('threadlisting', url=link, shared=True)

    def parse_thread(self, response):
        threadid = self.get_id_from_url(response.url)
        # We first parse the first post. 
        messageitem = items.Message()
        #messageitem['postid'] = "msg" + threadid Cannot be yielded since there is none.
        messageitem['threadid'] = threadid
        messageitem['postid'] = "msg" + threadid # Note this!
        msg = response.xpath('.//div[@class="col-xs-10 alert alert-info whitebg"]')
        messageitem['contenttext'] = self.get_text(msg)
        messageitem['contenthtml'] = self.get_text(msg.extract_first())        

        # there are 3 user classes. Buyer, vendor and support.
        vendor  = response.xpath(".//div[@class='col-xs-12']/small/a/text()").extract_first() is not None
        support = response.xpath(".//div[@class='col-xs-12']/small/b/text()").extract_first() == 'Support'
        buyer   = vendor is False and support is False
        # Buyer username.
        if buyer is True:
            author_username = response.xpath(".//div[@class='col-xs-12']/small/text()").extract_first()
            author_username = re.search('by (.*)$', author_username).group(1)
            messageitem['author_username'] = author_username
            membergroup = "Buyer"
        # Support staff.
        elif support is True:
            author_username = response.xpath(".//div[@class='col-xs-12']/small/b/text()").extract_first().strip()
            messageitem['author_username'] = author_username
            membergroup = "Support"
        # vendor username.
        elif vendor is True: 
            author_username = response.xpath(".//div[@class='col-xs-12']/small/a/text()").extract_first()
            messageitem['author_username'] = author_username
            membergroup = "Vendor"
        else: 
            self.logger.warning('Unknown member group at %s' % response.url)
        # Get info about the post.
        postinfo = self.get_text(response.xpath(".//div[@class='col-xs-12']/small"))
        if postinfo:
            matches = re.search(r'(\d+) (.+) ago by ([^ ]+)', postinfo)
            messageitem['posted_on'] = self.parse_timestr(matches.group(0))
        else:
            self.logger.warning("No postinfo yielded at %s" % response.url)
        yield messageitem


        # Then we yield the first user.
        # To treat the DB nice and avoid race conditions, sleep for a second.
        time.sleep(0.5)
        user = items.User()
        user['username'] = author_username
        user['membergroup'] = membergroup
        if membergroup in ["Buyer", "Support"]:
            user['relativeurl'] = user['username']
            user['fullurl'] = self.spider_settings['endpoint'] + user['username']
        elif membergroup == "Vendor":
            user['relativeurl'] = response.xpath(".//div[@class='col-xs-12']/small/a/@href").extract_first()
            user['fullurl'] = self.spider_settings['endpoint'] + user['relativeurl']
        else:
            self.logger.warning('Unknown member group at %s' % response.url)

        poster_block = response.xpath(".//div[@class='col-xs-12']")
        if membergroup in ['Buyer', 'Vendor']:
            stars = poster_block.xpath('.//span[@class="nowrap btn-xs alert brightBlueBG"]/text()').extract_first()
            if stars:
                stars = re.search('[Vendor|Buyer]: ([0-9]{1,1000})', stars).group(1)
                user['stars'] = stars
            else:
                self.logger.warning('No stars at URL %s' % response.url)
        yield user

        # We now parse the comments and yield them to the DB.
        # To treat the DB nice and avoid race conditions, sleep for a second.
        time.sleep(0.5)
        post = response.css('.row .col-lg-8 > div')
        # # Parse the remaining comments.
        reply_index = 1
        for comment in post.css('div.comment p'):
            messageitem = items.Message()
            messageitem['threadid'] = threadid
            messageitem['postid'] = "reply_%s-%d" % (threadid, reply_index)
            reply_index += 1
            post_info = comment.css('small::text').extract_first()
            if post_info:
                matches = re.search(r'(\d+) point([s]*) (.+)', post_info)
                if matches:
                    messageitem['posted_on'] = self.parse_timestr(matches.group(3))
            author_name = comment.css('a.vendorname::text').extract_first()
            if not author_name:
                author_name = comment.css('*::text').extract_first()
            messageitem['author_username'] = author_name.strip()
            messageitem['contenttext'] = ''.join(comment.css('p::text').extract()[1:])
            messageitem['contenthtml'] = self.get_text(comment.css('p').extract_first())
            yield messageitem
        # Sleep again to avoid race condition.
        time.sleep(0.5)
        for comment in post.css('div.comment p'):
            useritem = items.User()
            vendor  = comment.xpath('.//a[@class="vendorname"]/text()').extract_first() is not None
            buyer   = comment.xpath('.//span[@class="left lightGrey"]').extract_first() is not None and self.get_text(comment).startswith('Support') is False
            support = comment.xpath('.//span/b') is not None and self.get_text(comment).startswith('Support') is True
            if vendor is True:
                useritem['username'] = comment.xpath('.//a[@class="vendorname"]/text()').extract_first()
                useritem['relativeurl'] = comment.xpath('.//a[@class="vendorname"]/@href').extract_first()
                useritem['fullurl'] = self.spider_settings['endpoint'] + useritem['relativeurl']
                membergroup = "Vendor"
                useritem['stars'] = comment.xpath('.//span[@class="nowrap btn-xs alert brightBlueBG"]/text()').extract_first().replace('Vendor: ', '')
            elif support is True:
                username = self.get_text(comment)
                username = re.search('^(Support)[0-9]{1,100} ', username).group(1)
                useritem['username'] = username
                useritem['relativeurl'] = useritem['username']
                useritem['fullurl'] = self.spider_settings['endpoint'] + useritem['username']
                membergroup = "Support"
            elif buyer is True:
                username = self.get_text(comment)
                username = re.search('^(.*?) Buyer', username).group(1)
                useritem['username'] = username
                useritem['relativeurl'] = useritem['username']
                useritem['fullurl'] = self.spider_settings['endpoint'] + useritem['username']
                membergroup = "Buyer"
                useritem['stars'] = comment.xpath('.//span[@class="nowrap btn-xs alert brightBlueBG"]/text()').extract_first().replace('Buyer: ', '')
            else:
                self.logger.warning("Unknown commenter group at %s" % response.url)
            useritem['membergroup'] = membergroup
            yield useritem

    def parse_timestr(self, timestr):
        parsed_time = None
        try:
            matches = re.search('(.+) (.+) ago', timestr.lower())
            delta = -1 * int(matches.group(1))
            unit = matches.group(2)
            if unit == 'minute' or unit == 'minutes':
                parsed_time = datetime.utcnow() + timedelta(minutes=delta)
            elif unit == 'hour' or unit == 'hours':
                parsed_time = datetime.utcnow() + timedelta(hours=delta)
            elif unit == 'day' or unit == 'days':
                parsed_time = datetime.utcnow() + timedelta(days=delta)
        except Exception:
            if timestr:
                self.logger.warning("Could not determine time from this string : '%s'. Ignoring" % \
                                    timestr)

        return parsed_time

    def require_redirect(self, response):
        return True if 'Refresh' in response.headers else False

    def get_redirect_link(self, response):
        if self.require_redirect(response):
            redirect = response.headers['Refresh']
            matches = re.search('url=(.*)', redirect).groups()
            return matches[0] if len(matches) > 0 else None

        return None

    def loggedin(self, response):
        settings_links = response.css('ul.nav.navbar-nav li a[href="/settings"]')
        if len(settings_links) > 0:
            return True
        else:
            return False

    def has_login_form(self, response):
        return True if len(response.css('form input[name="username"]')) > 0 else False

    def is_ddos_protection_form(self, response):
        return True if len(response.css('form input[name="captcha"]')) > 0 else False

    def create_request_from_ddos_protection(self, response):
        captcha_src = response.css('body center img::attr(src)').extract()[1].strip()

        req = FormRequest.from_response(response, formname='form', headers=self.user_agent)
        req.meta['captcha'] = {        # CaptchaMiddleware will take care of that.
            'request' : self.make_request('captcha', url=captcha_src),
            'name' : 'captcha',
            'preprocess' : 'WallstreetMarketAddBackground'
        }

        return req

    def create_request_from_login_page(self, response):
        data = {
            'username' : self.login['username'],
            'password' : self.login['password'],
        }

        req = FormRequest.from_response(response, formdata=data, formcss='form[i="login"]', headers=self.user_agent)

        return req

    def get_id_from_url(self, url):
        try:
            _id = url.split('/')[-1]
            return _id if _id.isdigit() else None
        except Exception:
            self.logger.warning("Could not determine id from this url : '%s'" % url)
