from datetime import datetime, timedelta
import re
from scrapy.http import FormRequest, Request
from scrapyprj.spiders.ForumSpider import ForumSpider
import scrapyprj.items.forum_items as items

class ZionMarketForumSpider(ForumSpider):
    name = "zionmarket_forum"

    custom_settings = {
        'MAX_LOGIN_RETRY' : 10,
        'RESCHEDULE_RULES' : {
            'The post table and topic table seem to be out of sync' : 60
        }
    }

    def __init__(self, *args, **kwargs):
        super(self.__class__, self).__init__(*args, **kwargs)

        self.logintrial = 0
        self.set_max_concurrent_request(3)      # Scrapy config
        self.set_download_delay(10)             # Scrapy config
        self.set_max_queue_transfer_chunk(1)    # Custom Queue system

        self.parse_handlers = {
            'index'         : self.parse_index,
            'threadlisting'    : self.parse_thread_listing,
            'thread'        : self.parse_thread
        }

    def start_requests(self):
        yield self.make_request('index')

    def make_request(self, reqtype, **kwargs):
        if 'url' in kwargs:
            kwargs['url'] = self.make_url(kwargs['url'])

        if 'redirect_from' in kwargs:
            req = Request(kwargs['url'])
            req.meta['redirect_from'] = kwargs['redirect_from']
            req.dont_filter = True
        elif reqtype == 'index':
            req = Request(self.make_url('index'))
            req.dont_filter = True
        elif reqtype == 'ddos_protection':
            req = self.create_request_from_ddos_protection(kwargs['response'])
            req.meta['ddos_protection'] = True
            req.dont_filter = True
        elif reqtype == 'captcha':
            req = Request(kwargs['url'])
            req.dont_filter = True
        elif reqtype == 'dologin':
            req = self.create_request_from_login_page(kwargs['response'])
            req.dont_filter = True
        elif reqtype in ['threadlisting', 'thread']:
            req = Request(kwargs['url'])
            req.dont_filter = True

        req.meta['reqtype'] = reqtype   # We tell the type so that we can redo it if login is required
        req.meta['proxy'] = self.proxy  # meta[proxy] is handled by scrapy.

        if 'priority' in kwargs:
            req.priority = kwargs['priority']

        if 'req_once_logged' in kwargs:
            req.meta['req_once_logged'] = kwargs['req_once_logged']

        return req

    def parse(self, response):
        if response.status in range(400, 600):
            self.logger.warning("%s response %s at URL %s" % (self.login['username'], response.status, response.url))
        else:
            self.logger.info("[Logged in = %s]: %s %s at %s URL: %s" % (self.loggedin(response), self.login['username'], response.status, response.request.method, response.url))

        if self.require_redirect(response):
            redirect = self.get_redirect_link(response)
            req_once_logged = response.meta['req_once_logged'] if 'req_once_logged' in response.meta else None
            self.logger.debug('Redirect to ' + redirect)

            yield self.make_request(response.meta['reqtype'], req_once_logged=req_once_logged,
                                    url=redirect, redirect_from=response.request)

            return

        if 'redirect_from' in response.request.meta:
            response.request = response.request.meta['redirect_from']

        if not self.loggedin(response):
            if self.is_ddos_protection_form(response):
                self.logger.warning('Encountered a DDOS protection page as %s' % self.login['username'])
                if self.logintrial > self.settings['MAX_LOGIN_RETRY']:
                    req_once_logged = response.meta['req_once_logged'] if 'req_once_logged' in response.meta else None
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
                    req_once_logged = response.meta['req_once_logged'] if 'req_once_logged' in response.meta else None
                    self.wait_for_input("Too many login failed", req_once_logged)
                    self.logintrial = 0
                    return

                self.logger.info("Trying to logTrying to login as %s." % self.login['username'])
                self.logintrial += 1

                if 'req_once_logged' in response.meta:
                    req_once_logged = response.meta['req_once_logged']

                yield self.make_request('dologin', req_once_logged=req_once_logged, response=response, priority=10)

            else:
                self.logger.warning('Something went wrong. See the exception and investigate %s. Dumping html: %s'
                                    % (response.url, response.body))
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
        for category_link in response.css('.table.forum > tbody > tr > td:nth-child(2) > a::attr(href)').extract():
            yield self.make_request(reqtype='threadlisting', url=category_link)

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

                author = cells[1].css('h4 div small a::text').extract_first()
                if not author:
                    byuser = cells[1].css('h4 div small::text').extract_first()
                    m = re.search(" ago by (.+)", byuser) # regex
                    if m:
                        author = m.group(1).strip()
                threaditem['author_username'] = author

                # Cannot get last update time exactly, that's because the update time
                # doesn't follow time format, it's something like "XX days ago".
                threaditem['last_update'] = self.parse_timestr(cells[3].css('small::text').extract()[-1])
                threaditem['replies'] = cells[2].css('::text')

                yield threaditem
                yield self.make_request('thread', url=thread_link)
            except Exception as ex:
                self.logger.warning("Error in retrieving theads. %s" % ex)

        for link in response.css("a.paginate[rel='next']::attr(href)").extract():
            yield self.make_request('threadlisting', url=link)

    def parse_thread(self, response):
        threadid = self.get_id_from_url(response.url)

        try:
            # Parse first post
            post = response.css('.row .col-lg-8 > div')

            messageitem = items.Message()
            post_info = ''.join(post.css('small.lightGrey *::text').extract())
            m = re.search(r'(\d+) (.+) ago by ([^ ]+)', post_info)
            if m:
                messageitem['posted_on'] = self.parse_timestr(m.group(0))
                messageitem['author_username'] = m.group(3).strip()
            else:
                self.logger.warning("Cannot determine created date and author on URL %s." % (response.url))

            messageitem['threadid'] = threadid
            messageitem['postid'] = 1    # Set postid to 1 for first post

            msg = post.css('.alert.alert-info')
            messageitem['contenttext'] = self.get_text(msg)
            messageitem['contenthtml'] = self.get_text(msg.extract_first())

            yield messageitem

            # Parse comments
            for comment in post.css('div.comment p'):
                messageitem = items.Message()

                vote_link = comment.css('span.lightGrey a::attr(href)').extract_first()
                messageitem['postid'] = vote_link.split('/')[-1].split('#')[0]
                messageitem['threadid'] = threadid

                post_info = comment.css('small::text').extract_first()
                m = re.search(r'(\d+) point([s]*) (.+)', post_info)
                if m:
                    messageitem['posted_on'] = self.parse_timestr(m.group(3))
                else:
                    self.logger.warning("Cannot determine created date and author on URL %s." % (response.url))

                author_name = comment.css('a.vendorname::text').extract_first()
                if not author_name:
                    author_name = comment.css('*::text').extract_first()
                messageitem['author_username'] = author_name.strip()

                messageitem['contenttext'] = ''.join(comment.css('p::text').extract()[1:])
                messageitem['contenthtml'] = self.get_text(comment.css('p').extract_first())

                yield messageitem

        except Exception as ex:
            self.logger.warning("Invalid thread page. %s" % ex)

    def parse_timestr(self, timestr):
        parsed_time = None
        try:
            m = re.search('(.+) (.+) ago', timestr.lower())
            delta = -1 * int(m.group(1))
            unit = m.group(2)
            if unit == 'minute' or unit == 'minutes':
                parsed_time = datetime.utcnow() + timedelta(minutes=delta)
            elif unit == 'hour' or unit == 'hours':
                parsed_time = datetime.utcnow() + timedelta(hours=delta)
            elif unit == 'day' or unit == 'days':
                parsed_time = datetime.utcnow() + timedelta(days=delta)
        except:
            if timestr:
                self.logger.warning("Could not determine time from this string : '%s'. Ignoring" % timestr)

        return parsed_time

    def require_redirect(self, response):
        return True if 'Refresh' in response.headers else False

    def get_redirect_link(self, response):
        if self.require_redirect(response):
            redirect = response.headers['Refresh']
            m = re.search('url=(.*)', redirect).groups()
            return m[0] if len(m) > 0 else None

        return None

    def loggedin(self, response):
        settings_links = response.css('ul.nav.navbar-nav li a[href="/settings"]')
        return settings_links and len(settings_links) > 0

    def has_login_form(self, response):
        return True if len(response.css('form input[name="username"]')) > 0 else False

    def is_ddos_protection_form(self, response):
        return True if len(response.css('form input[name="captcha"]')) > 0 else False

    def create_request_from_ddos_protection(self, response):
        captcha_src = response.css('body center img::attr(src)').extract()[1].strip()

        req = FormRequest.from_response(response, formname='form')
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

        req = FormRequest.from_response(response, formdata=data, formcss='form[i="login"]')

        return req

    def get_id_from_url(self, url):
        try:
            _id = url.split('/')[-1]
            return _id if _id.isdigit() else None
        except:
            self.logger.warning("Could not determine id from this url : '%s'" % url)
