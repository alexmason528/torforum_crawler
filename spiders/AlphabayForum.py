#http://pwoah7foa6au2pul.onion

from __future__ import absolute_import
import scrapy
import time
from scrapy.http import FormRequest,Request
from scrapy.conf import settings
import logging
import torforum_crawler.thirdparties.deathbycaptcha as deathbycaptcha
from pprint import pprint
from fake_useragent import UserAgent
import torforum_crawler.alphabayforum.helpers.LoginQuestion as LoginQuestion
import torforum_crawler.alphabayforum.helpers.DatetimeParser as AlphabayDatetimeParser
from scrapy.shell import inspect_response
import torforum_crawler.database.db as db
from torforum_crawler.database.orm import *
from torforum_crawler.ColorFormatterWrapper import ColorFormatterWrapper
import hashlib 
from urlparse import urlparse
import traceback
import re
from peewee import *
import torforum_crawler.alphabayforum.items as items
from torforum_crawler.database.dao import DatabaseDAO
from datetime import datetime

class AlphabayForum(scrapy.Spider):
    name = "alphabay_forum"

    alphabay_settings = settings['ALPHABAYFORUM']
    user_agent  = UserAgent().random
    logintrial = 0
    pipeline = None  # Set by the pipeline open_spider() callback

    custom_settings = {
        'ITEM_PIPELINES': {
            'torforum_crawler.alphabayforum.pipelines.map2db.map2db': 400,  # Convert from Items to Models
            'torforum_crawler.pipelines.save2db.save2db': 401   # Sends models to DatabaseDAO. DatabaseDAO must be explicitly flushed from spider.  self.dao.flush(Model)
        }
    }

    def __init__(self, *args, **kwargs):
    #  self.dbc= deathbycaptcha.SocketClient('a', 'b');
        self.email = self.alphabay_settings['logins'][0]['email']        #todo use login manager 
        self.password = self.alphabay_settings['logins'][0]['password']  #todo use login manager
        self.username = self.alphabay_settings['logins'][0]['username']  #todo use login manager


        self.dao = DatabaseDAO(self)
        self.forum = self.dao.forum  # Get back the ORM object representing the forum we are crawling.
        self.fromtime = settings['fromtime'] if 'fromtime' in settings else None
        self.crawltype = settings['crawltype'] if 'crawltype' in settings else  'full'
        self.crawlitem = [ 'thread', 'message'] #todo, use configuration

        self.trycolorizelogs() # monkey patching to have color in the logs.

        super(AlphabayForum, self).__init__(*args, **kwargs)

    def make_request(self, reqtype,  **kwargs):
        
        if 'url' in kwargs:
            kwargs['url'] = self.make_url(kwargs['url'])

        if reqtype == 'index':
            req = Request(self.make_url('index'))
        
        elif reqtype == 'dologin':
            data = {
                'login' : self.email,
                'register' : '0',
                'password' : self.password,
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

        elif reqtype in  ['forumlisting', 'userprofile']:
            req = Request(kwargs['url'])
        elif reqtype == 'threadpage':
            req = Request(kwargs['url'])
            req.meta['threadid'] = kwargs['threadid']
        else:
            raise Exception('Unsuported request type ' + reqtype)


        req.meta['reqtype'] = reqtype   # We tell the type so that we can redo it if login is required
        req.dont_filter=True
        proxy = getattr(self, 'proxy', None)
        if proxy:
            req.meta['proxy'] = proxy

        return req

    def make_url(self, url):
        endpoint = self.alphabay_settings['endpoint'].strip('/');
        prefix = self.alphabay_settings['prefix'].strip('/');
        if url.startswith('http'):
            return url
        elif url in self.alphabay_settings['ressources'] :
            return endpoint + '/' + prefix + '/' + self.ressource(url).lstrip('/')
        elif url.startswith('/'):
            return endpoint + '/' +  url.lstrip('/')
        else:
            return endpoint + '/' + prefix + '/' + url.lstrip('/')


    def start_requests(self):
        yield self.make_request('index')
   
    def parse(self, response):
        #self.printstats()
        if not self.islogged(response):
            if self.logintrial > settings['MAX_LOGIN_RETRY']:
                raise Exception("Too many failed login trials. Giving up.")
            self.logger.info("Trying to login.")
            self.logintrial += 1
            yield self.make_request(reqtype='dologin', req_once_logged=response.request);  # We try to login and save the original request
        else : 
            self.logintrial = 0

            if response.meta['reqtype'] == 'index':
                links = response.css("li.forum h3.nodeTitle a::attr(href)")
                for link in links:
                    yield self.make_request(reqtype='forumlisting', url=link.extract())
            elif  response.meta['reqtype'] == 'forumlisting':
                for x in self.parse_forumlisting(response) : yield x
                     
            elif response.meta['reqtype'] == 'userprofile':
                pass

            elif response.meta['reqtype'] == 'threadpage':
                for x in self.parse_threadpage(response) : yield x 


    def parse_forumlisting(self, response):
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
            
                link                            = threaddiv.css(".title a.PreviewTooltip")
                url                             = link.xpath("@href").extract_first()
                threaditem['relativeurl']       = url
                threaditem['fullurl']           = self.make_url(url)
                threaditem['title']             = link.xpath("text()").extract_first()
                threaditem['author_username']   = threaddiv.css(".username::text").extract_first()
                author_url = threaddiv.css(".username::attr(href)").extract_first()
                
                try:
                    m = re.match('threads/([^/]+)(/page-\d+)?', urlparse(url).query.strip('/'))
                    m2 = re.match("(.+\.)?(\d+)$", m.group(1))
                    threaditem['threadid'] = m2.group(2)
                except Exception as e:
                    raise Exception("Could not extract thread id from url : %s. \n %s " % (url, e.message))

                if author_url and 'userprofile' in self.crawlitem: # If not crawled, an empty entry will be created if not exist in the database by the mapper to ensure respect of foreign key.
                    request_buffer.append( self.make_request('userprofile',  url = author_url))

                if url and 'thread' in self.crawlitem: 
                    request_buffer.append( self.make_request('threadpage', url=url, threadid=threaditem['threadid'])) # First page of thread

                yield threaditem # sends data to pipelne
                

            except Exception as e:
                self.logger.error("Failed parsing response forumlisting at " + response.url + ". Error is "+e.message+".\n Skipping thread\n" + traceback.format_exc())
                continue
        
        # Parse next page.
        nextpageurl =  response.xpath("//nav//a[contains(., 'Next >')]/@href").extract_first()
        if nextpageurl and self.shouldcrawl(oldestthread_datetime): #No record time to provide here.
            request_buffer.append( self.make_request(reqtype='forumlisting', url = nextpageurl)  )
        
        self.dao.flush(models.Thread)  # Flush threads to database.

        #We yield requests AFTER writing to database. This will avoid race condition that could lead to foreign key violation. (Thread post linked to a thread not written yet.)
        for request in request_buffer:  
            yield request


    def parse_threadpage(self, response):
        threadid = response.meta['threadid']
        for message in response.css(".messageList .message"):

            msgitem = items.Message();
            try:
                try:
                    fullid = message.xpath("@id").extract_first()
                    msgitem['postid'] = re.match("post-(\d+)", fullid).group(1)
                except:
                    raise Exception("Can't extract post id. " + e.message)
                msgitem['author_username'] = message.css(".messageDetails .username::text").extract_first()
                msgitem['posted_on'] = AlphabayDatetimeParser.tryparse(message.css(".messageDetails .DateTime::attr(title)").extract_first())
                textnode = message.css(".messageContent")
                msgitem['contenthtml'] = textnode.extract_first()
                msgitem['contenttext'] = ''.join(textnode.xpath("*//text()[normalize-space(.)]").extract()).strip()
                msgitem['threadid'] = threadid
            except Exception as e:
                self.logger.error("Failed parsing response for thread at " + response.url + ". Error is "+e.message+".\n Skipping thread\n" + traceback.format_exc())

            yield msgitem

        self.dao.flush(models.Message)
        nextpageurl =  response.xpath("//nav//a[contains(., 'Next >')]/@href").extract_first()

        if nextpageurl:
            yield self.make_request("threadpage", url=nextpageurl, threadid=threadid)

        #Start looking for next page.

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
        if username and username.strip() == self.username:
            logged = True
        
        if logged:
            self.logger.debug("Logged In")
        else:
            self.logger.debug("Not Logged In")

        return logged

    def ressource(self, name):
        if name not in self.alphabay_settings['ressources']:
            raise Exception('Cannot access ressource ' + name + '. Ressource is not specified in config.')  
        return self.alphabay_settings['ressources'][name]
    
    #Monkey patch to have color in the logs.
    def trycolorizelogs(self):
        try:
            colorformatter = ColorFormatterWrapper(self.logger.logger.parent.handlers[0].formatter)
            self.logger.logger.parent.handlers[0].setFormatter(colorformatter)
        except:
            pass

    def shouldcrawl(self, recordtime=None, dbrecordtime=None):
        if self.crawltype == 'full':
            return True
        elif self.crawltype == 'delta':
            return isinvalidated(recordtime, dbrecordtime)
        else:
            raise Exception("Unknown crawl type :" + self.crawltype )

    def isinvalidated(self, ecordtime=None, dbrecordtime=None):
        if not recordtime:
            return True
        else:
            if self.fromtime:
                return (self.fromtime < recordtime)
            else:
                if not dbrecordtime:
                    return True
                else:
                    return (dbrecordtime < recordtime)

