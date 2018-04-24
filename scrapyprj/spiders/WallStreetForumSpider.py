from __future__ import absolute_import
from scrapy.http import FormRequest, Request
from scrapyprj.spiders.ForumSpider import ForumSpider
import scrapyprj.items.forum_items as items
from datetime import timedelta
import dateutil
import time
from scrapy.shell import inspect_response


class WallStreetForumSpider(ForumSpider):
    name = "wallstreet_forum"

    custom_settings = {
        'MAX_LOGIN_RETRY': 10,
        'IMAGES_STORE': './files/img/wallstreet_forum',
        'RANDOMIZE_DOWNLOAD_DELAY': True,
        'DELAY_SECONDS': 5,
        'HTTPERROR_ALLOW_ALL' : True,
        'RETRY_ENABLED' : True,
        'RETRY_TIMES' : 5        
    }

    def __init__(self, *args, **kwargs):
        super(self.__class__, self).__init__(*args, **kwargs)

        self.set_max_concurrent_request(1)      # Scrapy config
        self.set_download_delay(20)             # Scrapy config
        self.set_max_queue_transfer_chunk(16)    # Custom Queue system
        self.statsinterval = 60                 # Custom Queue system

        self.logintrial = 0
        self.parse_handlers = {
                'dologin': self.parse_index,
                'threadlisting': self.parse_thread_listing,
                'thread': self.parse_thread,
                'userprofile': self.parse_userprofile,
                'index': self.parse_index
            }

    def start_requests(self):
        yield self.make_request('index')

    def make_request(self, reqtype,  **kwargs):
        if 'url' in kwargs:
            kwargs['url'] = self.make_url(kwargs['url'])

        if reqtype == 'index':
            req = Request(self.make_url('index'), dont_filter=True)
        elif reqtype == 'loginpage':
            req = Request(self.make_url('login'), dont_filter=True)
        elif reqtype == 'dologin':
            req = self.make_login_request_from_form(kwargs['response'])
            req.dont_filter = True
        elif reqtype in ['threadlisting', 'thread', 'userprofile']:
            req = Request(self.make_url(kwargs['url']))
            req.meta['shared'] = True
            if 'relativeurl' in kwargs:
                req.meta['relativeurl'] = kwargs['relativeurl']
        else:
            raise Exception('Unsuported request type ' + reqtype)

        req.meta['reqtype'] = reqtype   # We tell the type so that we can redo it if login is required
        req.meta['proxy'] = self.proxy  # meta[proxy] is handled by scrapy.

        if 'req_once_logged' in kwargs:
            req.meta['req_once_logged'] = kwargs['req_once_logged']        

        return req

    def parse(self, response):
        if response.status in range(400, 600):
            self.logger.warning("%s response %s at URL %s" % (self.login['username'], response.status, response.url))
        else:
            self.logger.info("[Logged in = %s]: %s %s at %s URL: %s" % (self.is_logged_in(response), self.login['username'], response.status, response.request.method, response.url))
        if self.is_banned(response) is True:
            self.logger.warning("%s has been banned from %s. Please abort the crawl and make a new login. Then crawl with lighter settings. URL is not parsed." % (self.login['username'], response.url))

        if self.is_logged_in(response) and response.status == 200:
            # self.logger.info("Logged in.")
            self.logintrial = 0
            it = self.parse_handlers[response.meta['reqtype']].__call__(response)
            if it:
                for x in it:
                    if x is not None:
                        yield x
        elif self.is_login_page(response):
            # self.logger.info("Login page.")
            req_once_logged = response.meta['req_once_logged'] if 'req_once_logged'  in response.meta else response.request 

            if self.logintrial > self.settings['MAX_LOGIN_RETRY']:
                self.wait_for_input("Too many login failed", req_once_logged)
                self.logintrial = 0
                return
            self.logger.info("Trying to login.")
            self.logintrial += 1

            yield self.make_request(reqtype='dologin', response=response, req_once_logged=req_once_logged);  # We try to login and save the original request
        else:
            self.logger.info("Not logged, going to login page.")
            yield self.make_request(reqtype='loginpage', req_once_logged=response.request)

    def is_login_page(self, response):
        field_username_exist = response.xpath("//input[@name='req_username']/@name").extract_first()
        field_password_exist = response.xpath("//input[@name='req_password']/@name").extract_first()
        return (field_username_exist and field_password_exist)

    def is_logged_in(self, response):
        """
            In case of logged in, logged_in would be "Logout", else, it would be None.
        """
        logged_in = response.xpath("//ul/li[@id='navlogout']/a/text()").extract_first()
        return (logged_in is not None)

    def is_banned(self, response):
        banned = response.xpath(".//div[@class='main-content main-message']").extract_first()
        if banned is not None:
            if banned == "You are banned from this forum.":
                return True
        else:
            return False

    def make_login_request_from_form(self, response):
        form_data = {
            "form_sent": response.xpath("//input[@name='form_sent']/@value").extract_first(),
            # "redirect_url": response.xpath("//input[@name='redirect_url']/@value").extract_first(),
            "redirect_url": self.make_url('index'),
            "csrf_token": response.xpath("//input[@name='csrf_token']/@value").extract_first(),
            'req_username': self.login['username'],
            'req_password': self.login['password'],
            'login': 'Login',
        }
        # self.logger.info(form_data)
        req = FormRequest.from_response(response, formdata=form_data)
        return req

    def parse_index(self, response):
        if 'req_once_logged' in response.meta:
            yield response.meta['req_once_logged']

        for url in response.xpath("//div[@class='item-subject']/h3[@class='hn']/a/@href").extract():
            yield self.make_request('threadlisting', url=url)

    def parse_thread_listing(self, response):
        for line in response.xpath("//div[contains(@id,'forum')]/div[contains(@id,'topic')]"):
            threaditem = items.Thread()

            threaditem['title'] = self.get_text(line.xpath("div[@class='item-subject']/h3[@class='hn']/a"))

            # e.g. from Today 02:43:16, Yesterday 22:40:25, 2018-04-13 12:50:11 etc
            threaditem['last_update'] = self.parse_timestr(self.get_text(line.xpath("ul[@class='item-info']/li[@class='info-lastpost']/strong/a")))

            threadlinkhref = line.xpath("div[@class='item-subject']/h3[@class='hn']/a/@href").extract_first()
            threaditem['fullurl'] = threadlinkhref
            threaditem['relativeurl'] = threadlinkhref.replace(self.spider_settings['endpoint'], "/")
            threaditem['threadid'] = self.get_url_param(threaditem['fullurl'], 'id')
            threaditem['replies'] = self.get_text(line.xpath("ul[@class='item-info']/li[@class='info-replies']/strong"))
            threaditem['views'] = self.get_text(line.xpath("ul[@class='item-info']/li[@class='info-views']/strong"))
            threaditem['author_username'] = self.get_text(line.xpath("div[@class='item-subject']/p/span/cite"))
            yield threaditem
            yield self.make_request('thread', url=threadlinkhref)

        next_page = response.xpath("//div[@id='brd-pagepost-top']/p[@class='paging']/a[contains(text(), 'Next')]/@href").extract_first()
        if next_page:
            yield self.make_request("threadlisting", url=next_page)

    def parse_timestr(self, timestr):
        last_post_time = None
        try:
            timestr = timestr.lower()
            timestr = timestr.replace('today', str(self.localnow().date()))
            timestr = timestr.replace('yesterday', str(self.localnow().date() - timedelta(days=1)))
            last_post_time = self.to_utc(dateutil.parser.parse(timestr))
        except Exception as e:
            if timestr:
                self.logger.warning("Could not determine time from this string : '%s'. Ignoring -> %s" % (timestr, str(e)))
        return last_post_time

    def parse_thread(self, response):
        threadid = self.get_url_param(response.url, 'id')
        posts = response.xpath("//div[contains(@id,'forum')]/div[contains(@class,'post')]")
        for post in posts:
            try:
                messageitem = items.Message()
                posttime = self.parse_timestr(self.get_text(post.xpath("div[@class='posthead']//span[@class='post-link']/a[@class='permalink']")))

                userprofile_link = post.xpath("div[@class='posthead']//span[@class='post-byline']/em/a/@href").extract_first()

                messageitem['author_username'] = self.get_text(post.xpath("div[@class='posthead']//span[@class='post-byline']/em/a/text()").extract_first())
                messageitem['postid'] = post.xpath("div[@class='posthead']/@id").extract_first()
                if messageitem["postid"]:
                    messageitem["postid"] = messageitem["postid"].replace("p", "")

                messageitem['threadid'] = threadid
                messageitem['posted_on'] = posttime

                msg = post.xpath(".//div[@class='entry-content']")
                messageitem['contenttext'] = self.get_text(msg)
                messageitem['contenthtml'] = self.get_text(msg.extract_first())

                yield messageitem
                yield self.make_request('userprofile', url=userprofile_link, relativeurl=userprofile_link.replace(self.spider_settings['endpoint'], "/"))
            except Exception as e:
                self.logger.warning("Invalid thread page. %s" % str(e))

        next_page = response.xpath("//div[@id='brd-pagepost-top']/p[@class='paging']/a[contains(text(), 'Next')]/@href").extract_first()
        if next_page:
            yield self.make_request("thread", url=next_page)

    def parse_userprofile(self, response):
        #time.sleep(self.settings["DELAY_SECONDS"])
        user = items.User()
        user['relativeurl'] = response.meta['relativeurl']
        user['fullurl'] = response.url

        lis = response.xpath("//div[contains(@class,'profile')]//ul[@class='user-ident ct-legend']/li")
        for li in lis:
            class_name = li.xpath("@class").extract_first()
            if class_name:
                class_name = class_name.lower()
                text = self.get_text(li)
                if "username" in class_name:
                    user["username"] = text
                elif "usertitle" in class_name:
                    user["title"] = text
                elif any(s in class_name for s in ['avatar', 'email', 'pm']):
                    pass
                else:
                    self.logger.warning('New information found on user profile page : %s' % class_name)


        spans = response.xpath("//div[contains(@class,'profile')]//ul[@class='data-list']/li/span")
        for span in spans:
            label = span.xpath("text()").extract_first()
            if label:
                label = label.lower()
                text = self.get_text(span.xpath("strong"))
                if "registered:" in label:
                    user["joined_on"] = self.parse_timestr(text)
                elif "last post:" in label:
                    user["last_post"] = self.parse_timestr(text)
                elif "posts:" in label:
                    user["post_count"] = text
                elif "from:" in label:
                    user["location"] = text
                elif "real name:" in label:
                    user["realname"] = text
                elif any(s in label for s in ['avatar', 'email', 'pm']):
                    pass
                else:
                    self.logger.warning('New information found on user profile page : %s' % label)

        signature = response.xpath("//div[contains(@class,'profile')]//div[@class='sig-demo']")
        if signature:
            user['signature'] = self.get_text(signature)

        yield user
