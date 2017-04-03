import scrapy
from scrapy import signals
from peewee import *
from scrapyprj.database.markets.orm.models import *
from datetime import datetime
from scrapyprj.database.settings import markets as dbsettings
from scrapyprj.database.dao import DatabaseDAO
from scrapyprj.database import db
from scrapyprj.ColorFormatterWrapper import ColorFormatterWrapper
from scrapyprj.spiders.BaseSpider import BaseSpider

from importlib import import_module
from fake_useragent import UserAgent
import os, time, sys
from dateutil import parser
import random
import logging
from Queue import Queue
import itertools as it
import pytz

from twisted.internet import reactor

class MarketSpider(BaseSpider):
	user_agent  = UserAgent().random
	def __init__(self, *args, **kwargs):
		super(MarketSpider, self).__init__( *args, **kwargs)
		self._baseclass = MarketSpider

		db.init(dbsettings)

		if 'dao' in kwargs:
			self.dao = kwargs['dao']
		else:
			self.dao = self.make_dao()

		if not hasattr(self._baseclass, '_request_queue'):
			self._baseclass._request_queue = Queue()

		self.set_timezone()

		try:
			self.market = Market.get(spider=self.name)
		except:
			raise Exception("No market entry exist in the database for spider %s" % self.name)

		if not hasattr(self._baseclass, '_cache_preloaded') or not self._baseclass._cache_preloaded:
			self.dao.cache.reload(User, User.market == self.market)
			self._baseclass._cache_preloaded = True
		

		self.register_new_scrape()
		self.start_statistics()


	@classmethod
	def from_crawler(cls, crawler, *args, **kwargs):
		spider = cls(*args, settings = crawler.settings,**kwargs)
		spider.crawler = crawler
		crawler.signals.connect(spider.spider_closed, signal=signals.spider_closed)
		crawler.signals.connect(spider.spider_idle, signal=signals.spider_idle)			# We will fetch some users/thread that we need to re-read from the database.

		return spider


	def make_dao(self):
		donotcache = [
			AdsProperty,
			AdsPropertyAudit,
			AdsFeedbackProperty,
			AdsFeedbackPropertyAudit,
			SellerFeedbackProperty,
			SellerFeedbackPropertyAudit
		]

		return DatabaseDAO(self, cacheconfig='markets', donotcache=donotcache)	

	def enqueue_request(self, request):
		self._baseclass._request_queue.put(request)

	def consume_request(self, n):
		i = 0

		while i<n and not self._baseclass._request_queue.empty():
			yield self._baseclass._request_queue.get()
			i += 1

	def spider_idle(self, spider):
		pagesize = 100

		for req in self.consume_request(pagesize):
			self.crawler.engine.crawl(req, spider)


	#Called by Scrapy Engine when spider is closed	
	def spider_closed(self, spider, reason):
		self.scrape.end = datetime.utcnow();
		self.scrape.reason = reason
		self.scrape.save()

		if self.process_created:
			self.process.end = datetime.utcnow()
			self.process.save()

		if self.savestat_taskid:
			self.savestat_taskid.cancel()
		self.savestats()

		BaseSpider.spider_closed(self, spider, reason)

		
	# Insert a database entry for this scrape.
	def register_new_scrape(self):
		self.process_created=False 	# Indicates that this spider created the process entry. Will be responsible of adding end date
		if not hasattr(self, 'process'):	# Can be created by a script and passed to the constructor
			self.process = Process()
			self.process.start = datetime.utcnow()
			self.process.pid = os.getpid()
			self.process.cmdline = ' '.join(sys.argv)
			self.process.save()
			self.process_created = True

		self.scrape = Scrape();	# Create the new Scrape in the databse.
		self.scrape.start = datetime.utcnow()
		self.scrape.process = self.process
		self.scrape.market = self.market
		self.scrape.login = self._loginkey
		self.scrape.proxy = self._proxy_key
		self.scrape.save();		


	def start_statistics(self):
		self.statsinterval = 30
		if 'statsinterval' in self.settings:
			self.statsinterval = int(self.settings['statsinterval'])

		self.savestats_handler()	


	def savestats(self):
		stat = ScrapeStat(scrape=self.scrape)

		stat.ads						= self.dao.stats[Ads]						if Ads 						in self.dao.stats else 0
		stat.ads_propval				= self.dao.stats[AdsProperty]				if AdsProperty 				in self.dao.stats else 0
		stat.ads_feedback				= self.dao.stats[AdsFeedback]				if AdsFeedback 				in self.dao.stats else 0
		stat.ads_feedback_propval		= self.dao.stats[AdsFeedbackProperty]		if AdsFeedbackProperty 		in self.dao.stats else 0
		stat.user						= self.dao.stats[User]						if User 					in self.dao.stats else 0
		stat.user_propval				= self.dao.stats[UserProperty]				if UserProperty 			in self.dao.stats else 0
		stat.seller_feedback			= self.dao.stats[SellerFeedback]			if SellerFeedback 			in self.dao.stats else 0
		stat.seller_feedback_propval	= self.dao.stats[SellerFeedbackProperty]	if SellerFeedbackProperty 	in self.dao.stats else 0

		stat.request_sent 		= self.crawler.stats.get_value('downloader/request_count') 	or 0 if hasattr(self, 'crawler') else 0
		stat.request_bytes 		= self.crawler.stats.get_value('downloader/request_bytes') 	or 0 if hasattr(self, 'crawler') else 0
		stat.response_received 	= self.crawler.stats.get_value('downloader/response_count') or 0 if hasattr(self, 'crawler') else 0
		stat.response_bytes 	= self.crawler.stats.get_value('downloader/response_bytes') or 0 if hasattr(self, 'crawler') else 0
		stat.item_scraped 		= self.crawler.stats.get_value('item_scraped_count') 		or 0 if hasattr(self, 'crawler') else 0

		stat.save()

	def savestats_handler(self):
		self.savestat_taskid = None
		self.savestats()
		self.savestat_taskid = reactor.callLater(self.statsinterval, self.savestats_handler)
