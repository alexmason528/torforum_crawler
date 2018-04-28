from datetime import datetime, timedelta
from dateutil import parser
import re
from urlparse import urlparse
from scrapy.http import FormRequest, Request
from scrapyprj.spiders.ForumSpider import ForumSpider
import scrapyprj.items.forum_items as items

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
            'thread'        : self.parse_thread,
            'userprofile'   : self.parse_userprofile
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
        elif reqtype in ['threadlisting', 'thread', 'userprofile']:
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
                    #byuser = cells[1].css('h4 div small::text').extract_first(
                    byuser = cells[1].xpath('.//h4/div/small//text()').extract()
                    byuser = ''.join(byuser)
                    if byuser:
                        matches = re.search(" ago by (.+)", byuser) # regex
                        if matches:
                            threaditem['author_username'] = matches.group(1).strip()
                    if "Support" in byuser:
                        self.logger.warning("Encountered a post by support.")

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

        # Parse first post
        post = response.css('.row .col-lg-8 > div')

        messageitem = items.Message()
        post_info = ''.join(post.css('small.lightGrey *::text').extract())
        if post_info:
            matches = re.search(r'(\d+) (.+) ago by ([^ ]+)', post_info)
            if matches:
                messageitem['posted_on'] = self.parse_timestr(matches.group(0))
                messageitem['author_username'] = matches.group(3).strip()

        messageitem['threadid'] = threadid
        messageitem['postid'] = "msg" + threadid

        msg = post.css('.alert.alert-info')
        messageitem['contenttext'] = self.get_text(msg)
        messageitem['contenthtml'] = self.get_text(msg.extract_first())

        yield messageitem

        # vendor_link = post.css('a.vendorname::attr(href)').extract_first()
        # if vendor_link:
        #     yield self.make_request('userprofile', url=vendor_link, shared=True)
        # else:
        #     star_rating = post.css('small.lightGrey span.alert::text').extract_first()
        #     if star_rating:
        #         matches = re.search(r'(\w+): (\d+)', star_rating)
        #         if matches:
        #             membergroup = matches.group(1)
        #             rating_count = int(matches.group(2))

        #             user = items.User()
        #             user['username'] = messageitem['author_username']
        #             user['membergroup'] = membergroup
        #             user['rating_count'] = rating_count

        #             yield user

        # Parse comments
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

            # commented_by_link = comment.css('a.vendorname::attr(href)').extract_first()
            # if commented_by_link:
            #     yield self.make_request('userprofile', url=commented_by_link, shared=True)
            # else:
            #     commented_by = comment.css('p *::text').extract()[0]
            #     star_rating = comment.css('p > span.alert::text').extract_first()
            #     if star_rating:
            #         matches = re.search(r'(\w+): (\d+)', star_rating)
            #         if matches:
            #             membergroup = matches.group(1)
            #             rating_count = int(matches.group(2))

            #             user = items.User()
            #             user['username'] = commented_by
            #             user['membergroup'] = membergroup
            #             user['rating_count'] = rating_count

            #             yield user

    def parse_userprofile(self, response):
        try:
            user = items.User()
            user['relativeurl'] = urlparse(response.url).path
            user['fullurl'] = response.url
            user['username'] = response.css('div.container div.row h3 a::text').extract_first()

            star_rating = response.css('div.container div.row h3 span.alert::text').extract_first()
            if star_rating:
                matches = re.search(r'(\w+): (\d+)', star_rating)
                if matches:
                    membergroup = matches.group(1)
                    user['membergroup'] = membergroup
                    user['rating_count'] = int(matches.group(2))

            userinfo = response.css('div.container div.row span.right span.right')
            user['location'] = userinfo.css('b::text').extract_first()
            member_since = userinfo.css('small::text').extract_first()
            user['joined_on'] = parser.parse(member_since[13:]) # Skip 'Member since '
            user['last_activity'] = userinfo.css('span.greenText::text').extract_first()

            user['pgp_key'] = response.css('div#content4 textarea::text').extract_first()

            # ratings = response.css('div.container div.alert.alert-warning')
            # if ratings:
            #     for rating in ratings.css('table tbody tr td span.blackT'):
            #         rating_name = rating.css('small::text')
            #         rating_value = rating.css('b::text')

            #         if rating_name == 'Positive':
            #             user['positive_feedback'] = rating_value
            #         elif rating_name == 'Neutral':
            #             user['neutral_feedback'] = rating_value
            #         elif rating_name == 'Negative':
            #             user['negative_feedback'] = rating_value

            #if membergroup == 'Vendor':
            #    user['user_sales'] = len(response.css('div.container div.prodwide'))

            yield user

        except Exception as ex:
            self.logger.warning("Error in retrieving user. %s" % ex)

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