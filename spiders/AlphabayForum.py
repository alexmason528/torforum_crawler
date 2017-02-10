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
import hashlib 

class AlphabayForum(scrapy.Spider):
    name = "alphabay_forum"

    alphabay_settings = settings['ALPHABAYFORUM']
    dbc = deathbycaptcha.SocketClient(settings['DEATHBYCAPTHA']['username'],settings['DEATHBYCAPTHA']['password'])
    ua = UserAgent()
    user_agent  = ua.random
    request_stack = list()
    db.init(settings['DATABASE']); 
    logintrial = 0

    test=0

    settings['MAX_LOGIN_RETRY'] = 9

    def __init__(self, *args, **kwargs):
    #  self.dbc= deathbycaptcha.SocketClient('a', 'b');
        self.email = self.alphabay_settings['logins'][0]['email']        #todo randomize
        self.password = self.alphabay_settings['logins'][0]['password']  #todo randomize
        self.username = self.alphabay_settings['logins'][0]['username']  #todo randomize

        self.trycolorizelogs() # monkey patching to have color in the logs.

        super(AlphabayForum, self).__init__(*args, **kwargs)

    def make_request(self, reqtype,args=None):
        
        if args and 'url' in args:
            args['url'] = self.make_url(args['url'])

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

            if self.test==0:        # temporary. We force a bad apssword to get a captcha to check the logic
                data['password'] = 'asdasdasd'
                self.test +=1

            if args and 'captcha_question_hash' in args:
                data['captcha_question_hash'] = args['captcha_question_hash']

            if args and 'captcha_question_answer' in args:
                data['captcha_question_answer'] = args['captcha_question_answer']
            
            req = FormRequest(self.make_url('login-postform'), formdata=data, callback=self.handle_login_response, dont_filter=True)
            req.method = 'POST'
            req.meta['req_once_logged'] = args['req_once_logged']

        elif reqtype == 'forumlisting':
            req = Request(args['url'])

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
        if not self.islogged(response):
            if self.logintrial > settings['MAX_LOGIN_RETRY']:
                raise Exception("Too many failed login trials. Giving up.")
            self.logger.info("Trying to login.")
            self.logintrial += 1
            yield self.make_request(reqtype='dologin', args={'req_once_logged' : response.request});  # We try to login and save the original request
        else : 
            self.logintrial = 0

            if response.meta['reqtype'] == 'index':
                links = response.css("li.forum h3.nodeTitle a::attr(href)")
                for link in links:
                    yield self.make_request(reqtype='forumlisting', args={'url':link.extract()})
            elif  response.meta['reqtype'] == 'forumlisting':
                self.logger.critical("Parsing next page! Oh yes. " + response.url)


    def handle_login_response(self, response):
        if self.islogged(response):
            self.logger.info('Login success, continuing where we were.')
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
                    db_question = LoginQuestion.lookup(self.name, dbhash)
                    answer = ""
                    if db_question.answer:
                        answer = db_question.answer
                        self.logger.info('Question was part of database. Using answer : ' + answer)
                    else:
                        if not db_question.question:
                            db_question.update(question=question).where(CaptchaQuestion.id==db_question.id).execute()
                        answer = LoginQuestion.answer(question)
                        self.logger.info('Trying to guess the answer. Best bet is : "' + answer + '"')
                    yield self.make_request(reqtype='dologin', args={'req_once_logged' : response.meta['req_once_logged'], 'captcha_question_hash' : qhash, 'captcha_question_answer' : answer});  # We try to login and save the original request

                else : 
                    self.logger.warning("Login failed. A new login form has been given, but with no captcha. Trying again.")
                    yield self.make_request(reqtype='dologin', args={'req_once_logged' : response.meta['req_once_logged']});  # We try to login and save the original request

            else :
                self.logger.error("Login failed and no login form has been given. Retrying")
                yield self.make_request(reqtype='dologin', args={'req_once_logged' : response.meta['req_once_logged']});  # We try to login and save the original request
                
            # Send new login request
        
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
