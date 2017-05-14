
from __future__ import absolute_import
import scrapy
from scrapy.http import FormRequest,Request
from scrapy.shell import inspect_response
from scrapyprj.spiders.ForumSpider import ForumSpider
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

class TradeRouteForumSpider(ForumSpider):
    name = "traderoute_forum"

    custom_settings = {
        'MAX_LOGIN_RETRY' : 10
    }

    known_users = {}

    def __init__(self, *args, **kwargs):
        super(self.__class__, self).__init__(*args, **kwargs)

        self.logintrial = 0

        self.parse_handlers = {
                'index'         : self.parse_index,
                'dologin'       : self.parse_index,
                'threadlisting' : self.parse_thread_listing,
                'thread'        : self.parse_thread,
                'loginpage'     : self.parse_loginpage # void function
            }

    def start_requests(self):
        yield self.make_request('index')

    def make_request(self, reqtype,  **kwargs):
        
        if 'url' in kwargs:
            kwargs['url'] = self.make_url(kwargs['url'])

        if reqtype == 'index':
            req = Request(self.make_url('index'), dont_filter=True)
        elif reqtype == 'loginpage':
            req = Request(self.make_url('loginpage'), dont_filter=True)
        elif reqtype == 'dologin':
            req = self.craft_login_request_from_form(kwargs['response'])
            req.meta['dont_redirect']=True
            req.dont_filter=True
        elif reqtype in ['threadlisting', 'thread']:
            req = Request(self.make_url(kwargs['url']))
            req.meta['shared'] = True
            if 'relativeurl' in kwargs:
                req.meta['relativeurl'] = kwargs['relativeurl']
        else:
            raise Exception('Unsuported request type ' + reqtype)

        if 'req_once_logged' in kwargs:
            req.meta['req_once_logged'] = kwargs['req_once_logged']

        req.meta['reqtype'] = reqtype   # We tell the type so that we can redo it if login is required
        req.meta['proxy'] = self.proxy  #meta[proxy] is handled by scrapy.

        return req
   
    def parse(self, response):
        # skip login for now
        if 0 and not self.islogged(response):
            if self.is_login_page(response):
                if self.logintrial > self.settings['MAX_LOGIN_RETRY']:
                    raise Exception("Too many failed login trials. Giving up.")
                self.logger.info("Trying to login.")
                self.logintrial += 1

                req_once_logged = response.meta['req_once_logged'] if 'req_once_logged'  in response.meta else response.request 
                
                yield self.make_request(reqtype='dologin',response=response, req_once_logged=req_once_logged);  # We try to login and save the original request
            elif 'req_once_logged' in response.meta:
                if self.is_loggedin_page(response):
                    self.logger.info("Logged In! Sleeping 1 seconds")
                    yield response.meta['req_once_logged']
            else:
                self.logger.info("Not logged, going to login page.")
                yield self.make_request(reqtype='loginpage', req_once_logged=response.request)

        else : 
            if 'req_once_logged' in response.meta:
                yield response.meta['req_once_logged']

            self.logintrial = 0
            it = self.parse_handlers[response.meta['reqtype']].__call__(response)
            if it:
                for x in it:
                    if x != None:
                        yield x

    def parse_loginpage(self, response):    # We should never be looking at a login page while we are logged in.
        pass

    def parse_index(self, response):
        for line in response.css("#brdmain tbody tr"):
            link = line.css("h3>a::attr(href)").extract_first()
            
            yield self.make_request('threadlisting', url=link);
    
    def parse_thread_listing(self, response):
        threads_requests = []
        
        for line in response.css("#brdmain tbody tr"):
            threadlinkobj = next(iter(line.css("td:first-child a") or []), None)  # Get Thread Name link, or None if not present
            if threadlinkobj:
                threaditem = items.Thread()            
                threadlinkhref = threadlinkobj.xpath("@href").extract_first() if threadlinkobj else None
                
                threaditem['title'] = self.get_text(threadlinkobj)
                threaditem['relativeurl'] = threadlinkhref
                threaditem['fullurl']   = self.make_url(threadlinkhref)
                
                threaditem['threadid'] = self.get_url_param(threaditem['fullurl'], 'id')

                byuser = self.get_text(line.css("td:first-child span.byuser"))
                m = re.match("by (.+)", byuser)
                if m:
                    threaditem['author_username'] = m.group(1)
                
                threaditem['last_update'] = self.parse_timestr(self.get_text(line.css("td:last-child a")))
                
                threaditem['replies']   = self.get_text(line.css("td:nth-child(2)"))
                threaditem['views']     = self.get_text(line.css("td:nth-child(3)"))
                yield threaditem

                threads_requests.append(self.make_request('thread', url=threadlinkhref))

        self.dao.flush(models.Thread)

        for req in threads_requests:
            yield req

        for link in response.css("#brdmain .pagelink a::attr(href)").extract():
            yield self.make_request('threadlisting', url=link)

    def parse_thread(self, response):
        threadid =  self.get_url_param(response.url, 'id')
        posts = response.css("#brdmain div.blockpost")
        for post in posts:
            try:
                messageitem = items.Message()
                posttime = self.parse_timestr(self.get_text(post.css("h2 a")))

                userprofile_link = post.css(".postleft dt:first-child a::attr(href)").extract_first()
                messageitem['author_username'] = self.get_text(post.css(".postleft dt:first-child"))

                messageitem['postid'] = post.xpath("@id").extract_first()
                messageitem['threadid'] = threadid
                messageitem['posted_on'] = posttime

                msg = post.css("div.postmsg")
                messageitem['contenttext'] = self.get_text(msg)
                messageitem['contenthtml'] = msg.xpath('./*').extract_first()

                yield messageitem

                user = self.handle_user(post)
                if user :
                    yield user
                    self.dao.flush(models.User)
                        
            except e:
                self.logger.warning("Invalid thread page. %s" % e)

        
        self.dao.flush#(models.Message)

        for link in response.css("#brdmain .pagelink a::attr(href)").extract():
            yield self.make_request('thread', url=link)

    def handle_user(self, post):
        username = self.get_text(post.css(".postleft dt:first-child"))

        if username in TradeRouteForumSpider.known_users:
            return None

        TradeRouteForumSpider.known_users[username] = True

        user = items.User()
        user['relativeurl'] = ''
        user['fullurl'] = ''
        user['username'] = username

        user['title'] = self.get_text(post.css(".postleft dd.usertitle"))
        user['joined_on'] = self.get_text(post.css(".postleft dd:nth-child(3)"))
        user['post_count'] = self.get_text(post.css(".postleft dd:nth-child(4)"))

        return user

    def craft_login_request_from_form(self, response):
        data = {
            'req_username' : self.login['username'],
            'req_password' : self.login['password']
        }
        req = FormRequest.from_response(response, formdata=data)

        return req

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

    def islogged(self, response):
        contenttext = self.get_text(response.css("#brdwelcome"))
        if 'Logged in as' in contenttext:
            return True
        return False

    def is_login_page(self, response):
        if len(response.css("form#login")) > 0:
            return True
        return False

    def is_loggedin_page(self, response):
        if len(response.css('meta[http-equiv="refresh"]')) > 0:
            return True
        return False

    def get_url_param(self, url, key):
         return dict(parse_qsl(urlparse(url).query))[key]

