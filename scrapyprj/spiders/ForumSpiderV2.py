import scrapy
from scrapy import signals
from peewee import *
from scrapyprj.database.forums.orm.models import *
from datetime import datetime
from scrapyprj.database.settings import forums as dbsettings
from scrapyprj.database.dao import DatabaseDAO
from scrapyprj.database import db
from scrapyprj.spiders.BaseSpider import BaseSpider
from scrapy.exceptions import DontCloseSpider
from scrapyprj.middlewares.replay_spider_middleware import ReplaySpiderMiddleware
from scrapy.http import FormRequest,Request

import os, time, sys
from dateutil import parser
from scrapy import signals
from Queue import Queue
import itertools as it

from twisted.internet import reactor
from scrapy.dupefilters import RFPDupeFilter
from Queue import PriorityQueue
from IPython import embed
import json
import profiler
from scrapyprj.spiders.ForumSpider import ForumSpider

class ForumSpiderV2(ForumSpider):
    
    def __init__(self, *args, **kwargs):
        super(ForumSpiderV2, self).__init__(*args, **kwargs)

    def start_requests(self):
        yield self.make_request(url = 'index', dont_filter=True)
    
    def parse_response(self, response):
        return
        yield

    def parse(self, response):
        for x in self.parse_response(response):
            if x != None:
                if isinstance(x, Request):
                    if 'proxy' not in x.meta:
                        x.meta['proxy'] = self.proxy
                        x.meta['slot'] = self.proxy
                yield x
        
        hrefs = response.css('a::attr(href)').extract()
        for uri in hrefs:
            full_url = self.make_url(uri)
            if self.should_follow(uri):
                yield self.make_request(url = uri)
        

    def make_request(self, **kwargs):
        if 'url' in kwargs:
            kwargs['url'] = self.make_url(kwargs['url'])

        req = Request(kwargs['url'])

        if 'dont_filter' in kwargs:
            req.dont_filter = kwargs['dont_filter']

        req.meta['proxy'] = self.proxy  #meta[proxy] is handled by scrapy.
        req.meta['slot'] = self.proxy

        return req

    def should_follow(self, uri):
        exclude = self.spider_settings['exclude']
        if 'prefix' in exclude:
            for prefix in exclude['prefix']:
                if uri.startswith(prefix):
                    return False
        if 'regex' in exclude:
            for regex in exclude['regex']:
                pass
        return True