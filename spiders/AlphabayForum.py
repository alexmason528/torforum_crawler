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
from scrapy.shell import inspect_response
import torforum_crawler.database.db as db
from torforum_crawler.database.orm.models import CaptchaQuestion
from torforum_crawler.ColorFormatterWrapper import ColorFormatterWrapper

class AlphabayForum(scrapy.Spider):
    name = "alphabay_forum"
    specific_settings = settings['ALPHABAYFORUM']
    dbc = deathbycaptcha.SocketClient(settings['DEATHBYCAPTHA']['username'],settings['DEATHBYCAPTHA']['password'])
    ua = UserAgent()
    user_agent  = 'Mozilla/5.0 (Windows NT 6.1; rv:45.0) Gecko/20100101 Firefox/45.0' #ua.random
    request_stack = list()
    db.init(settings['DATABASE']); 

    def __init__(self, *args, **kwargs):
    #  self.dbc= deathbycaptcha.SocketClient('a', 'b');
        self.email = self.specific_settings['logins'][0]['email']        #todo
        self.password = self.specific_settings['logins'][0]['password']  #todo
        self.username = self.specific_settings['logins'][0]['username']  #todo

        self.trycolorizelogs() # monkey patching to have color in the logs.

        super(AlphabayForum, self).__init__(*args, **kwargs)

    def start_requests(self):
        req = Request(self.make_url('index'))
        req = self.initreq(req)

        yield req
    
    def parse(self, response):
        req = Request(self.make_url('index'), dont_filter=True)
        if not self.islogged(response):
            yield self.start_login_loop(req_once_logged=req);


    def start_login_loop(self, req_once_logged):
        self.logger.info("Trying to login.")
        req = self.login_request(self.email, self.password, cb=self.handle_login_response)
        if req_once_logged:
            self.request_stack.append(req_once_logged)
        return req
        


    def login_request(self, email, password, cb):
        
        data = {
            'login' : email,
            'register' : '0',
            'password' : password,
            'cookie_check' : '1',
            '_xfToken': "",
            'redirect' : self.ressource('index') 
        }
        
        req = FormRequest(self.make_url('login-postform'), formdata=data, callback=cb, dont_filter=True)
        req = self.initreq(req)
        req.method = 'POST'

        return req

    #Request Callback
    def handle_login_response(self, response):
        if self.islogged(response):
            self.logger.info('Login success, continuing where we were.')
            if len(self.request_stack):
                yield self.request_stack.pop()
            else:
                self.logger.error("No request was stored in the request stack. Can't continue")
        else :   # Not logged, check for captcha

            loginform = response.css("form[id='pageLogin']")
            if loginform:
                captcha = loginform.css("#Captcha")
                if captcha:
                    question = captcha.css('label::text').extract_first()
                    qhash = captcha.css("input[name='captcha_question_hash']::attr(value)").extract_first()
                    self.logger.info('Login failed. A captcha question has been asked.  Question : ' + question)  
                    db_question = LoginQuestion.lookup(self.name, qhash)
                    answer = ""
                    if db_question.answer:
                        answer = db_question.answer
                        self.logger.info('Captcha was part of database. Using answer : ' + answer)
                    else:
                        db_question.question = question
                        db_question.save()
                        answer = LoginQuestion.answer(question)
                        self.logger.info('Trying to guess the answer. Best bet is ' + answer)


                else : 
                    self.logger.warning("Login failed. A new login form has been given, bu with no captcha. Trying again.")
                    #todo
            else :
                self.logger.error("Login failed and no login form has been given. Don't know what to do next.")
        
            # Send new login request
        inspect_response(response, self)


    def islogged(self, response):
        self.logger.debug("Checking if logged in")
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
        if name not in self.specific_settings['ressources']:
            msg = 'Cannot access ressource ' + name + '. Ressource is not specified in config.'
            self.logger.error(msg)
            raise Exception(msg)
            
        return self.specific_settings['ressources'][name]
    
    def make_url(self, name):
        return self.specific_settings['endpoint'].strip('/') + '/' + self.ressource(name).strip('/')


    def initreq(self, req):
        proxy = getattr(self, 'proxy', None)
        if proxy:
            req.meta['proxy'] = proxy

        return req

    #Monkey patch to have color in the logs.
    def trycolorizelogs(self):
        try:
            colorformatter = ColorFormatterWrapper(self.logger.logger.parent.handlers[0].formatter)
            self.logger.logger.parent.handlers[0].setFormatter(colorformatter)
        except:
            pass
