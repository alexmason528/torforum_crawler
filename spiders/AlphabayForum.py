#http://pwoah7foa6au2pul.onion

from __future__ import absolute_import
import scrapy
from scrapy.http import FormRequest,Request
from scrapy.shell import inspect_response
import torforum_crawler.alphabay_forum.helpers.LoginQuestion as LoginQuestion
import torforum_crawler.alphabay_forum.helpers.DatetimeParser as AlphabayDatetimeParser
from torforum_crawler.spiders.BaseSpider import BaseSpider
from torforum_crawler.database.orm import *
import torforum_crawler.alphabay_forum.items as items
from datetime import datetime
from urlparse import urlparse
import logging
import time
import hashlib 
import traceback
import re

from IPython import embed

class AlphabayForum(BaseSpider):
    name = "alphabay_forum"
    logintrial = 0

    custom_settings = {
        'ITEM_PIPELINES': {
            'torforum_crawler.alphabay_forum.pipelines.map2db.map2db': 400,  # Convert from Items to Models
            'torforum_crawler.pipelines.save2db.save2db': 401   # Sends models to DatabaseDAO. DatabaseDAO must be explicitly flushed from spider.  self.dao.flush(Model)
        }
    }

    def __init__(self, *args, **kwargs):
        super(self.__class__, self).__init__(*args, **kwargs)

        self.crawlitem = [ 'thread', 'userprofile'] #todo, use configuration

    def start_requests(self):
        yield self.make_request('index')

        for url in self.get_all_users_url():    # We refresh already known users.
            yield self.make_request('userprofile', url=url)

    def make_request(self, reqtype,  **kwargs):
        
        if 'url' in kwargs:
            kwargs['url'] = self.make_url(kwargs['url'])

        if reqtype == 'index':
            req = Request(self.make_url('index'))
            req.dont_filter=True
        
        elif reqtype == 'dologin':
            data = {
                'login' : self.login['email'],
                'register' : '0',
                'password' : self.login['password'],
                'cookie_check' : '1',
                '_xfToken': "",
                'redirect' : self.ressource('index') 
            }

            if 'captcha_question_hash' in kwargs:
                data['captcha_question_hash'] = kwargs['captcha_question_hash']

            if 'captcha_question_answer' in kwargs:
                data['captcha_question_answer'] = kwargs['captcha_question_answer']
            
            req = FormRequest(self.make_url('login-postform'), formdata=data, callback=self.handle_login_response, dont_filter=True)
            req.method = 'POST' # Has to be uppercase !
            req.meta['req_once_logged'] = kwargs['req_once_logged']
            req.dont_filter=True

        elif reqtype in  ['parse_threadlisting', 'userprofile']:
            req = Request(kwargs['url'])

        elif reqtype == 'threadpage':
            req = Request(kwargs['url'])
            req.meta['threadid'] = kwargs['threadid']
        else:
            raise Exception('Unsuported request type ' + reqtype)

        req.meta['reqtype'] = reqtype   # We tell the type so that we can redo it if login is required
        req.meta['proxy'] = self.proxy  #meta[proxy] is handled by scrapy.

        return req
   
    def parse(self, response):
        if not self.islogged(response):
            if self.logintrial > self.settings['MAX_LOGIN_RETRY']:
                raise Exception("Too many failed login trials. Giving up.")
            self.logger.info("Trying to login.")
            self.logintrial += 1
            yield self.make_request(reqtype='dologin', req_once_logged=response.request);  # We try to login and save the original request
        else : 
            self.logintrial = 0

            if response.meta['reqtype'] == 'index':
                links = response.css("li.forum h3.nodeTitle a::attr(href)")
                for link in links:
                    yield self.make_request(reqtype='parse_threadlisting', url=link.extract())
            elif  response.meta['reqtype'] == 'parse_threadlisting':
                for x in self.parse_threadlisting(response) : yield x
                     
            elif response.meta['reqtype'] == 'userprofile':
                for x in self.parse_userprofile(response) : yield x

            elif response.meta['reqtype'] == 'threadpage':
                for x in self.parse_threadpage(response) : yield x 

    def parse_threadlisting(self, response):
        threaddivs = response.css("li.discussionListItem")
        oldestthread_datetime = datetime.now()
        request_buffer = []
        for threaddiv in threaddivs:
            try:
                threaditem = items.Thread();
                last_message_datestr        = threaddiv.css(".lastPostInfo .DateTime::text").extract_first()
                threaditem['last_update']   = AlphabayDatetimeParser.tryparse(last_message_datestr)
                oldestthread_datetime       = threaditem['last_update']  # We assume that threads are ordered by time.
                if not threaditem['last_update']:
                    raise Exception("Could not parse time string : " + last_message_datestr)
            
                link    = threaddiv.css(".title a.PreviewTooltip")
                url     = link.xpath("@href").extract_first()
                navspan = threaddiv.css("span.itemPageNav") #Nav buttons means many page. Start with the last one for delta crawl.
                request_url = url
                if navspan: 
                    request_url = navspan.css("a")[-1].xpath("@href").extract_first();   # Get last page url

                threaditem['relativeurl']       = url
                threaditem['fullurl']           = self.make_url(url)
                threaditem['title']             = link.xpath("text()").extract_first()
                threaditem['author_username']   = threaddiv.css(".username::text").extract_first()
                author_url = threaddiv.css(".username::attr(href)").extract_first()
                
                threaditem['threadid'] = self.read_threadid_from_url(url)

                if author_url and 'userprofile' in self.crawlitem: # If not crawled, an empty entry will be created if not exist in the database by the mapper to ensure respect of foreign key.
                    request_buffer.append( self.make_request('userprofile',  url = author_url))

                if request_url and self.shouldcrawl(threaditem['last_update']):  # If new post in thread
                    request_buffer.append( self.make_request('threadpage', url=request_url, threadid=threaditem['threadid'])) # First page of thread

                yield threaditem # sends data to pipelne
                
            except Exception as e:
                self.logger.error("Failed parsing response parse_threadlisting at " + response.url + ". Error is "+e.message+".\n Skipping thread\n" + traceback.format_exc())
                continue
        
        # Parse next page.
        nextpageurl =  response.xpath("//nav//a[contains(., 'Next >')]/@href").extract_first()
        if nextpageurl and self.shouldcrawl(oldestthread_datetime): 
            request_buffer.append( self.make_request(reqtype='parse_threadlisting', url = nextpageurl)  )
        
        self.dao.flush(models.Thread)  # Flush threads to database.

        #We yield requests AFTER writing to database. This will avoid race condition that could lead to foreign key violation. (Thread post linked to a thread not written yet.)
        for request in request_buffer:  
            yield request

    # Parse messages from a thread page.
    def parse_threadpage(self, response):   
        threadid = response.meta['threadid']

        oldestpost_datetime = datetime.now()
        for message in response.css(".messageList .message"):

            msgitem = items.Message();
            try:
                try:
                    fullid = message.xpath("@id").extract_first()
                    msgitem['postid'] = re.match("post-(\d+)", fullid).group(1)
                except:
                    raise Exception("Can't extract post id. " + e.message)
                msgitem['author_username'] = message.css(".messageDetails .username::text").extract_first().strip()
                msgitem['posted_on'] = self.read_message_datetime(message.css(".messageDetails .DateTime"))
                if msgitem['posted_on']:
                    if msgitem['posted_on'] < oldestpost_datetime:
                        oldestpost_datetime = msgitem['posted_on']  # Get smallest date e.g. oldest

                if not msgitem['posted_on']:
                    embed()
                textnode = message.css(".messageContent")
                msgitem['contenthtml'] = textnode.extract_first()
                msgitem['contenttext'] = ''.join(textnode.xpath("*//text()[normalize-space(.)]").extract()).strip()
                msgitem['threadid'] = threadid
            except Exception as e:
                self.logger.error("Failed parsing response for thread at " + response.url + ". Error is "+e.message+".\n Skipping thread\n" + traceback.format_exc())

            yield msgitem

        self.dao.flush(models.Message)

        if 'userprofile' in self.crawlitem:
            userprofilelinks = response.css("a.username::attr(href)").extract()
            userprofilelinks = list(set(userprofilelinks)) #removes duplicates
            for link in userprofilelinks:
                yield self.make_request('userprofile', url=self.make_url(link))

        #Start looking for previous page.
        if self.shouldcrawl(oldestpost_datetime):   # Will be false if delta crawl and date is too big 
            prevpageurl =  response.xpath("//nav//a[contains(., '< Prev')]/@href").extract_first()
            if prevpageurl:
                yield self.make_request("threadpage", url=prevpageurl, threadid=threadid)

    def parse_userprofile(self, response):
        content = response.css(".profilePage")
        if content:
            content= content[0]
            useritem = items.User()
            useritem['username'] = content.css(".username").xpath(".//text()").extract_first().strip()
            urlparsed =  urlparse(response.url)
            useritem['relativeurl'] = "%s?%s" % (urlparsed.path, urlparsed.query)
            useritem['fullurl'] = response.url

            try:
                useritem['title'] = content.css(".userTitle").xpath(".//text()").extract_first().strip()
            except:
                pass
            
            try:    
                useritem['banner'] = content.css(".userBanner").xpath(".//text()").extract_first().strip()
            except:
                pass

            try:
                m = re.match('members/([^/]+)', urlparse(response.url).query.strip('/'))
                m2 = re.match("(.+\.)?(\d+)$", m.group(1))
                useritem['user_id'] = m2.group(2)
            except:
                pass

            infos = content.css(".infoBlock dl")
            for info in infos:
                name = info.css('dt::text').extract_first().strip()
                try:
                    if name == 'Last Activity:':
                        datestr = info.css('dd .DateTime::attr(title)').extract_first().strip()
                        useritem['last_activity'] = AlphabayDatetimeParser.tryparse(datestr)
                    elif name == 'Joined:' :
                        datestr = info.css('dd').xpath(".//text()").extract_first().strip()
                        useritem['joined_on'] = AlphabayDatetimeParser.tryparse(datestr)
                    elif name == 'Messages:':
                        numberstr = info.css('dd').xpath(".//text()").extract_first().strip()
                        useritem['message_count'] = int(numberstr.replace(',', ''))
                    elif name == 'Likes Received:':
                        numberstr = info.css('dd').xpath(".//text()").extract_first().strip()
                        useritem['likes_received'] = int(numberstr.replace(',', ''))
                except:
                    pass


            yield useritem

        self.dao.flush(models.User) 

    def handle_login_response(self, response):
        if self.islogged(response):
            self.logger.info('Login success, continuing where we were.')
            self.dao.flush(models.CaptchaQuestion)
            if response.meta['req_once_logged']:
                yield response.meta['req_once_logged']
            else:
                self.logger.error("No request was given for when the login succeeded. Can't continue")
        else :   # Not logged, check for captcha

            loginform = response.css("form[id='pageLogin']")
            if loginform:
                captcha = loginform.css("#Captcha")
                if captcha:
                    question = captcha.css('label::text').extract_first()
                    qhash = captcha.css("input[name='captcha_question_hash']::attr(value)").extract_first()   # This hash is not repetitive
                    dbhash = hashlib.sha256(question).hexdigest() # This hash is reusable
                    self.logger.info('Login failed. A captcha question has been asked.  Question : "' + question + '"')  
                    db_question = self.dao.get_or_create(models.CaptchaQuestion, forum=self.forum, hash=dbhash)
                    answer = ""
                    if db_question.answer:
                        answer = db_question.answer
                        self.logger.info('Question was part of database. Using answer : ' + answer)
                    else:
                        if not db_question.question:
                            db_question.question = question
                            self.dao.enqueue(db_question)
                        answer = LoginQuestion.answer(question)
                        self.logger.info('Trying to guess the answer. Best bet is : "' + answer + '"')
                    yield self.make_request(reqtype='dologin', req_once_logged= response.meta['req_once_logged'], captcha_question_hash=qhash, captcha_question_answer=answer);  # We try to login and save the original request

                else : 
                    self.logger.warning("Login failed. A new login form has been given, but with no captcha. Trying again.")
                    yield self.make_request(reqtype='dologin', req_once_logged=response.meta['req_once_logged']);  # We try to login and save the original request

            else :
                self.logger.error("Login failed and no login form has been given. Retrying")
                yield self.make_request(reqtype='dologin', req_once_logged=response.meta['req_once_logged']);  # We try to login and save the original request
                
    def islogged(self, response):
        logged = False
        username = response.css(".accountUsername::text").extract_first()
        if username and username.strip() == self.login['username']:
            logged = True
        
        if logged:
            self.logger.debug("Logged In")
        else:
            self.logger.debug("Not Logged In")

        return logged

    def read_threadid_from_url(self, url):
        try:
            m = re.match('threads/([^/]+)(/page-\d+)?', urlparse(url).query.strip('/'))
            m2 = re.match("(.+\.)?(\d+)$", m.group(1))
            return m2.group(2)
        except Exception as e:
            raise Exception("Could not extract thread id from url : %s. \n %s " % (url, e.message))

    def read_message_datetime(self, div):
        title = div.xpath("@title")
        if title:
            return AlphabayDatetimeParser.tryparse(title.extract_first())

        datestring = div.xpath("@data-datestring").extract_first()
        timestring = div.xpath("@data-timestring").extract_first()

        if datestring and timestring:
            return AlphabayDatetimeParser.tryparse("%s %s" % (datestring, timestring))

        text = div.xpath(".//text()").extract_first()
        if text:
            return AlphabayDatetimeParser.tryparse(text)




