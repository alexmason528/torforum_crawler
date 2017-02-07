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

class AlphabayForum(scrapy.Spider):
    name = "alphabay_forum"
    specific_settings = settings['ALPHABAYFORUM']
    dbc = deathbycaptcha.SocketClient(settings['DEATHBYCAPTHA']['username'],settings['DEATHBYCAPTHA']['password'])
    ua = UserAgent()
    user_agent  = 'Mozilla/5.0 (Windows NT 6.1; rv:45.0) Gecko/20100101 Firefox/45.0' #ua.random
    request_stack = list()

    def __init__(self, *args, **kwargs):
    #  self.dbc= deathbycaptcha.SocketClient('a', 'b');
        self.email = self.specific_settings['logins'][0]['email']        #todo
        self.password = self.specific_settings['logins'][0]['password']  #todo
        self.username = self.specific_settings['logins'][0]['username']  #todo

        self.logger

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
            captcha = loginform.css("#Captcha")
            if captcha:
                question = captcha.css('label::text').extract_first()
                question_hash = captcha.css("input[name='captcha_question_hash']::attr(value)").extract_first()
                answer = LoginQuestion.Answer(question, question_hash)
        
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

