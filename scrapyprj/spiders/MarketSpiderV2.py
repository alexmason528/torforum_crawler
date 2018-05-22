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
from scrapyprj.spiders.MarketSpider import MarketSpider
import scrapy
from scrapy.http import FormRequest,Request
import re
from urlparse import urlparse, parse_qsl
import dateparser
from twisted.internet import reactor
from scrapy.dupefilters import RFPDupeFilter
from Queue import PriorityQueue
from IPython import embed
import json
import profiler
from scrapyprj.spiders.ForumSpider import ForumSpider


class MarketSpiderV2(MarketSpider):
    
    def __init__(self, *args, **kwargs):
        super(MarketSpiderV2, self).__init__(*args, **kwargs)

        self.alt_hostnames = []
        self.tor_browser = {
            'User-Agent':' Mozilla/5.0 (Windows NT 6.1; rv:52.0) Gecko/20100101 Firefox/52.0',
            'Accept':' text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language':' en-US,en;q=0.5',
            'Accept-Encoding':' gzip, deflate',
            'Connection':' keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }    

    def start_requests(self):
        yield self.make_request(url = 'index', dont_filter=True)
    
    def parse_response(self, response):
        return
        yield

    def set_priority(self, req):
        if 'priority' in self.spider_settings:
            priorities = self.spider_settings['priority']

            for key, priority in priorities.iteritems():
                if re.search(priority['regex'], req.url) is not None:
                    req.priority = priority['value']
                    # self.logger.info("[Priority: %s] %s" % (req.priority, req))
                    return req
        req.priority = 0
        #self.logger.info("[Priority: %s] %s" % (req.priority, req))
        return req

    def parse(self, response):
        # Verbose logging of HTTP responses.
        # self.repoprt_status can be set to False to turn off HTTP 200 reporting.
        if response.status in range(300, 600):
            self.logger.warning("[Logged in = %s|Priority %s]: %s: %s at %s" % (self.islogged(response), response.request.priority, self.login['username'], response.status, response.url))
        elif self.report_status is True:
            self.logger.info("[Logged in = %s|Priority %s]: %s %s at %s URL: %s" % (self.islogged(response), response.request.priority, self.login['username'], response.status, response.request.method, response.url))

        for x in self.parse_response(response):
            if x != None:
                if isinstance(x, Request):
                    if 'proxy' not in x.meta:
                        x.meta['proxy'] = self.proxy
                        x.meta['slot'] = self.proxy
                yield x
        # When we are logged in, we allow recursive collection of links which we follow.
        if self.recursive_flag is True:
            hrefs = response.css('a::attr(href)').extract()
            for uri in hrefs:
                if uri:
                    full_url = self.check_relative_url(uri, response)
                    if self.should_follow(uri, full_url):
                        yield self.make_request(url = full_url)          
        
    def check_relative_url(self, uri, response):
        if uri.startswith('?'): # relative path to current path
            current_path = urlparse(response.url)
            uri = current_path.path + uri
        
        return self.make_url(uri)

    def should_follow(self, relative_url, full_url):
        parsed_url = urlparse(full_url)
        endpoint = self.spider_settings['endpoint']
        if parsed_url.hostname is None:
            return False
        if parsed_url.hostname not in endpoint:
            if parsed_url.hostname not in self.alt_hostnames:
                if self.report_other_hostnames is True:
                    self.logger.warning('Not following url with different hostname, possibly an alt hostname : %s' % (full_url))
                self.alt_hostnames.append(parsed_url.hostname)
            return False

        exclude = self.spider_settings['exclude']
        if 'prefix' in exclude:
            for prefix in exclude['prefix']:
                if relative_url.startswith(prefix):
                    return False
                if parsed_url.path.startswith(prefix):
                    return False
        if 'regex' in exclude:
            for regex in exclude['regex']:
                if re.search(regex, relative_url) is not None:
                    return False
                if re.search(regex, parsed_url.path) is not None:
                    return False
        #self.logger.info('Following %s' % (url))
        return True

    def normalize_pgp_key(self, key):
        begin = '-----BEGIN PGP (PUBLIC|PRIVATE) KEY BLOCK-----'
        end = '-----END PGP (PUBLIC|PRIVATE) KEY BLOCK-----'
        m = re.search('(%s)(.+)(%s)' % (begin, end), key,re.S)
        if m:
            newlines = []
            for line in m.group(3).splitlines():
                if re.search('version', line, re.IGNORECASE):
                    continue
                elif re.search('comment', line, re.IGNORECASE):
                    continue
                newlines.append(line)
            content = ''.join(newlines)
            return '%s\n\n%s\n%s' % (m.group(1), content, m.group(4))        
        self.logger.warning('Failed to clean PGP key. \n %s' % key)
        return key   

    def parse_datetime(self, timestr):
        timestr = timestr.replace('less than', '')
        datetime = dateparser.parse(timestr)
        return datetime