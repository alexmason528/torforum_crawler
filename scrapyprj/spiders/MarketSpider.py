import scrapy
from scrapy import signals
from scrapy.exceptions import DontCloseSpider 
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
from Queue import PriorityQueue
import itertools as it
import pytz
from IPython import embed

from twisted.internet import reactor
from scrapy.mail import MailSender
from scrapy.downloadermiddlewares.cookies import CookiesMiddleware
from Cookie import SimpleCookie
from scrapy.http import Request


class MarketSpider(BaseSpider):
	user_agent  = UserAgent().random
	def __init__(self, *args, **kwargs):
		super(MarketSpider, self).__init__( *args, **kwargs)
		self._baseclass = MarketSpider
		self._baseclass._queue_size = 0

		db.init(dbsettings)

		if not hasattr(self, 'request_queue_chunk'):
			self.request_queue_chunk = 100

		if 'dao' in kwargs:
			self.dao = kwargs['dao']
		else:
			self.dao = self.make_dao()

		if not hasattr(self._baseclass, '_request_queue'):
			self._baseclass._request_queue = PriorityQueue()

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
		self.mailer =  MailSender.from_settings(self.settings)
		
		self.manual_input = None


	@classmethod
	def from_crawler(cls, crawler, *args, **kwargs):
		spider = cls(*args, settings = crawler.settings,**kwargs)
		spider.crawler = crawler
		crawler.signals.connect(spider.spider_closed, signal=signals.spider_closed)
		crawler.signals.connect(spider.spider_idle, signal=signals.spider_idle)			# We will fetch some users/thread that we need to re-read from the database.

		return spider

	@classmethod
	def make_dao(cls):
		donotcache = [
			AdsProperty,
			AdsPropertyAudit,
			AdsFeedbackProperty,
			AdsFeedbackPropertyAudit,
			SellerFeedbackProperty,
			SellerFeedbackPropertyAudit
		]

		dao = DatabaseDAO(cacheconfig='markets', donotcache=donotcache)
		dao.add_dependencies(AdsFeedback, [Ads])
		dao.add_dependencies(SellerFeedback, [User])
		dao.add_dependencies(AdsImage, [Ads])

		# These 2 callbacks will make sure to insert only the difference between the queue and the actual db content.
		# We assume that a complete dataset of Feedbacks objects related to an Ads or Seller is inside the queue because we will
		# delete database entries that are not in the queue.
		dao.before_flush(AdsFeedback, cls.AdsFeedbackDiffInsert)
		dao.before_flush(SellerFeedback, cls.SellerFeedbackDiffInsert)
		return 	dao

	@staticmethod
	def AdsFeedbackDiffInsert(queue):
		ads_list = list(set([x.ads.id for x in queue]))
		hash_list = list(set([x.hash for x in queue]))
		def diff(a,b): 	# This functions returns what "a" has but not "b"
			eq_map = {}
			for i in range(len(a)):
				for j in range(len(b)):
					if j not in eq_map and a[i].ads.id==b[j].ads.id and a[i].hash == b[j].hash:
						eq_map[i] = j
						break
				if i not in eq_map:
					yield a[i]


		db_content =  list(AdsFeedback.select()
			.where(AdsFeedback.ads <<  ads_list, AdsFeedback.hash << hash_list)
			.execute())

		to_delete = [row.id for row in diff(db_content, queue)]	# When its in the databse, but not in the queue : delete
		new_queue = list(diff(queue, db_content))	# When its in the queue but not in the database, keep it. Remove all the rest.
		
		if len(to_delete) > 0:
			AdsFeedback.delete().where(AdsFeedback.id << to_delete).execute()

		return new_queue
	
	@staticmethod
	def SellerFeedbackDiffInsert(queue):
		seller_list = list(set([x.seller.id for x in queue]))
		hash_list = list(set([x.hash for x in queue]))
		def diff(a,b):		# This functions returns what "a" has but not "b"
			eq_map = {}	
			for i in range(len(a)):
				for j in range(len(b)):
					if j not in eq_map and a[i].seller.id==b[j].seller.id and a[i].hash == b[j].hash:
						eq_map[i] = j
						break
				if i not in eq_map:
					yield a[i]


		db_content =  list(SellerFeedback.select()
			.where(SellerFeedback.seller <<  seller_list, SellerFeedback.hash << hash_list)
			.execute())

		to_delete = [row.id for row in diff(db_content, queue)]	# When its in the databse, but not in the queue : delete
		new_queue = list(diff(queue, db_content))		# When its in the queue but not in the database, keep it. Remove all the rest.
		
		if len(to_delete) > 0:
			SellerFeedback.delete().where(SellerFeedback.id << to_delete).execute()

		return new_queue		

	def enqueue_request(self, request):
		self._baseclass._queue_size += 1
		self._baseclass._request_queue.put( (-request.priority, request)  )	# Priority is inverted. High priority go first for scrapy. Low Priority go first for queue

	def consume_request(self, n):
		i = 0

		while i<n and not self._baseclass._request_queue.empty():
			priority, request = self._baseclass._request_queue.get()
			self._baseclass._queue_size -= 1
			yield request
			i += 1


	def spider_idle(self, spider):
		scheduled_request = False

		self.look_for_new_input()

		if not self.manual_input:
			spider.logger.debug('%s/%s Idle. Queue Size = %d' % (self._proxy_key, self._loginkey, self._baseclass._queue_size))
			for req in self.consume_request(self.request_queue_chunk):
				self.crawler.engine.crawl(req, spider)
				scheduled_request = True
			
		if scheduled_request or self.manual_input:		# manual_input is None if not waiting for cookies
			raise DontCloseSpider()						# Mandatory to avoid closing the spider if the request are being dropped and scheduler is empty.


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

	def wait_for_input(self, details):
		self.logger.warning("Waiting for manual input from database")

		self.manual_input					= ManualInput()
		self.manual_input.date_requested 	= datetime.utcnow()
		self.manual_input.spidername		= self.name
		self.manual_input.proxy 			= self._proxy_key
		self.manual_input.login 			= self._loginkey
		self.manual_input.user_agent 		= self.user_agent
		self.manual_input.cookies 			= self.get_cookies()
		self.manual_input.reload 			= False
		self.manual_input.save(force_insert=True)
		
		subject = "Spider crawling %s needs inputs. Id = %d" % (self.market.name, self.manual_input.id)

		msg 	= """
			Spider crawling market %s has requested new input to continue crawling.

			Configuration : 
				- Proxy : %s 
				- Login : %s 
				- User agent : %s
				- Cookies : %s
			
			Details : %s

			Please, go insert relevant data string in database for manual input id=%d.
			*** You can modify : proxy, login, user agent, cookies
			""" % (
				self.market.name, 
				self.manual_input.proxy, 
				self.manual_input.login, 
				self.manual_input.user_agent ,
				self.manual_input.cookies , 
				details, 
				self.manual_input.id
				)
		try:
			self.send_mail(subject, msg)
		except Exception, e:
			self.logger.error('Could not send email telling that we are waiting for input : %s' % e)


	def send_mail(self,subject, body):
		if self.mailer and 'MAIL_RECIPIENT' in self.settings:
			to	= self.settings['MAIL_RECIPIENT']
			self.logger.info('Sending email to %s. Subject : %s' % (to, subject))
			self.mailer.send(to=to, subject=subject, body=body)
		else:
			self.logger.warning('Trying to send email, but smtp is not configured or no MAIL_RECIPIENT is defined in settings.')


	def look_for_new_input(self):
		new_input = False
		if self.manual_input:
			
			new_manual_input = ManualInput.get(self.manual_input._pk_expr())	# Reload from database
			
			if new_manual_input.reload:
				self.logger.info("New input given! Continuing")
				error = False
				try:
					if new_manual_input.proxy != self._proxy_key:
						self.configure_proxy(new_manual_input.proxy)

					if new_manual_input.login != self._loginkey:
						self.configure_login(new_manual_input.login)

					if new_manual_input.cookies:
						self.set_cookies(new_manual_input.cookies)
					
					if new_manual_input.user_agent:
						self.user_agent
				except Exception, e:
					self.logger.error("Could not reload new data. %s" % e)
					error = True
				
				if error:
					self.manual_input.save()
				else:
					self.manual_input = None
					new_input = True
			else:
				self.logger.debug('No new input given by database.')
		return new_input

	def set_cookies(self, cookie_string):
		cookie_middleware = self.get_cookie_middleware()

		if not cookie_middleware:
			self.logger.error("Trying to set cookies, but can't find cookie middleware.")
		else:
			jar = cookie_middleware.jars[None]
			cookies = SimpleCookie(cookie_string.encode('ascii'))
			cookie_dict = dict()
			for key in cookies:
				cookie_dict[key] = cookies.get(key).value

			req = Request(self.spider_settings['endpoint'], cookies=cookie_dict)
			cookie_middleware.jars[None].clear()
			cookie_middleware.process_request(req, self)	# Simulate a request with these cookies.

	def get_cookies(self):
		cookie_middleware = self.get_cookie_middleware()

		if not cookie_middleware:
			self.logger.error("Trying to set cookies, but can't find cookie middleware.")
		else:
			jar = cookie_middleware.jars[None]

		req = Request(self.spider_settings['endpoint'])
		jar.add_cookie_header(req)

		return  req.headers['Cookie'] if 'Cookie' in req.headers else ''

	def get_cookie_middleware(self):
		cookie_middleware = None
		for middleware in self.crawler.engine.downloader.middleware.middlewares:
			if isinstance(middleware, CookiesMiddleware):
				cookie_middleware = middleware
				break

		return cookie_middleware





			




