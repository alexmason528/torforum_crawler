from __future__ import absolute_import
import scrapy
from scrapy.http import FormRequest,Request
from scrapy.shell import inspect_response
from scrapyprj.spiders.ForumSpiderV2 import ForumSpiderV2
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
from random import randint


class CannabisGrowersCoopForum(ForumSpiderV2):
    name = "cgmc_forum"
    
    custom_settings = {
        'MAX_LOGIN_RETRY' : 10,
		'IMAGES_STORE' : './files/img/cgmc_forum',
		'RANDOMIZE_DOWNLOAD_DELAY' : True
    }

    
    def __init__(self, *args, **kwargs):
        super(CannabisGrowersCoopForum, self).__init__(*args, **kwargs)

        self.set_max_concurrent_request(1)      # Scrapy config
        self.set_download_delay(12)             # Scrapy config
        self.set_max_queue_transfer_chunk(1)    # Custom Queue system
        self.statsinterval = 60 				# Custom Queue system

        self.logintrial = 0
    
    def parse_response(self, response):
        if self.is_login_page(response):
            yield self.do_login(response)

    def is_login_page(self, response):
        return response.css('form#login-form').extract_first() is not None
    
    def do_login(self, response):
        data = {
            'username' : self.login['username'],
            'password' : self.login['password'],
			'user_action' : 'login',
			'return' : 'login/'
        }

        req = FormRequest.from_response(response, formdata=data, formcss='form#login-form')
        req.dont_filter = True
        
        captcha_src = '/login/showCaptcha?' + str(randint(100000, 999999))

        req.meta['captcha'] = { 
            'request' : self.make_request(url = captcha_src, dont_filter = True),
            'name': 'captcha'
        }

        return req