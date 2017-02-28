import scrapy
from scrapy import signals
from peewee import *
from torforum_crawler.database.orm.models import *
from datetime import datetime
from scrapy.conf import settings
from torforum_crawler.database.dao import DatabaseDAO
from torforum_crawler.database import db
from torforum_crawler.statthread import StatThread
from torforum_crawler.ColorFormatterWrapper import ColorFormatterWrapper

from importlib import import_module
from fake_useragent import UserAgent
import os, time
from dateutil import parser
from IPython import embed
import random
import logging
import threading

from twisted.internet import reactor

class BaseSpider(scrapy.Spider):
	user_agent  = UserAgent().random
	def __init__(self, *args, **kwargs):
		super(BaseSpider, self).__init__( *args, **kwargs)
		self.load_spider_settings()
		self.initlogs()

		self.dao = DatabaseDAO(self, donotcache=[Message, UserProperty])

		if 'timezone' in self.spider_settings:
			os.environ['TZ'] = self.spider_settings['timezone']	# Set environment timezone.
			time.tzset()
			db.set_timezone() # Sync db timezone with environment.
		
		try:
			self.forum = Forum.get(spider=self.name)
		except:
			raise Exception("No forum entry exist in the database for spider " + spider.name)

		self.dao.initiliaze(self.forum) # Will preload some data in the database for performance gain

		self.login = self.get_login()

		self.crawltype = 'full'
		if 'crawltype' in settings:
			if settings['crawltype'] in ['full', 'delta']:
				self.crawltype = settings['crawltype']

		if not hasattr(self, 'proxy'):	# can be given by command line
			if 'PROXY' in settings:
				self.proxy = settings['PROXY']

		self.lastscrape = Scrape.select().where(Scrape.forum == self.forum and Scrape.end.is_null(False) and Scrape.reason=='finished').order_by(Scrape.start.desc()).first()

		self.fromtime = None;	# When doing a delta scrape, use this time as a reference
		if 'fromtime' in settings:
			if isinstance(settings['fromtime'], str):
				self.fromtime = parser.parse(settings['fromtime'])
			elif isinstance(datetime, settings['fromtime']):
				self.fromtime = settings['fromtime']
			else:
				raise ValueError("Cannot interpret timezone %s" % str(settings['fromtime']))
		elif self.lastscrape:
			self.fromtime = self.lastscrape.start

		if self.crawltype == 'delta' and self.fromtime:
			self.logger.info("Doing a delta crawl. Time reference is %s %s" % (str(self.fromtime), os.environ['TZ']))
		else:
			self.logger.info("Doing a full crawl")

		self.statsinterval = 30
		if 'statsinterval' in settings:
			self.statsinterval = int(settings['statsinterval'])


		self.scrape = Scrape();	# Create the new Scrape in the databse.
		self.scrape.start = datetime.now()
		self.scrape.forum = self.forum
		self.scrape.save();


		self.savestat_taskid = reactor.callLater(self.statsinterval, self.savestats_handler)
		#self.statthread.start()

	def closed( self, reason ):
		self.scrape.end = datetime.now();
		self.scrape.reason = reason
		self.scrape.save()

		if self.savestat_taskid:
			self.savestat_taskid.cancel()
		self.savestats()
		


	def initlogs(self):
		try:
			for logger_name in  settings['DISABLE_LOGGER'].split(','):
				logging.getLogger(logger_name).disabled=True
		except:
			pass

		try:
			colorformatter = ColorFormatterWrapper(self.logger.logger.parent.handlers[0].formatter)
			self.logger.logger.parent.handlers[0].setFormatter(colorformatter)
		except:
			pass

	def load_spider_settings(self):
		self.spider_settings = {}
		setting_module = "%s.%s.settings" % (settings['BOT_NAME'], self.name)
		try:
			self.spider_settings = import_module(setting_module).settings
		except:
			self.logger.warning("Cannot load spider specific settings from : %s" % setting_module)

	def ressource(self, name):
		if name not in self.spider_settings['ressources']:
			raise Exception('Cannot access ressource ' + name + '. Ressource is not specified in spider settings.')  
		return self.spider_settings['ressources'][name]

	def make_url(self, url):
		endpoint = self.spider_settings['endpoint'].strip('/');
		prefix = self.spider_settings['prefix'].strip('/');
		if url.startswith('http'):
			return url
		elif url in self.spider_settings['ressources'] :
			return "%s/%s/%s" % (endpoint, prefix, self.ressource(url).lstrip('/'))
		elif url.startswith('/'):
			return "%s/%s" % (endpoint, url.lstrip('/'))
		else:
			return "%s/%s/%s" % (endpoint,prefix, url.lstrip('/'))

	def shouldcrawl(self, recordtime=None, dbrecordtime=None):
		if self.crawltype == 'full':
			return True
		elif self.crawltype == 'delta':
			val =self.isinvalidated(recordtime, dbrecordtime)
			if val:
				self.logger.debug('Record dated from %s is considered invalidated. Crawling' % (str(recordtime)))
			else:
				self.logger.debug('Record dated from %s is considered up to date. Do not crawl' % (str(recordtime)))

			return val
		else:
			raise Exception("Unknown crawl type :" + self.crawltype )

	def isinvalidated(self, recordtime=None, dbrecordtime=None):
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


	#Return the requested login information from the spier settings.
	# attribute "login" must be given (-a login="paramValue" using the CLI)
	# attribute can be a numerical index or the login dict key. If not specified, a random entry is returned
	def get_login(self, force_new = False):
		if force_new or not hasattr(self, 'login') :
			if 'logins' not in self.spider_settings:
				raise Exception("No login defined in spider settings")

			if len(self.spider_settings['logins']) == 0:
				raise Exception("Empty login list in spider settings")			

			if 'login' in settings:
				if isinstance(settings['login'], int) or settings['login'].isdigit() :
					n = int(settings['login'])
					if n < 0 or n >= len(self.spider_settings['logins']):
						raise ValueError("No login information with index : %s" % settings['login'])
					key = list(self.spider_settings['logins'])[n]
					
				else :
					if settings['login'] not in self.spider_settings['logins']:
						raise ValueError("No login information with index : %s" % settings['login'])
					key = settings['login']
			else:
				n = random.randrange(0,len(self.spider_settings['logins']))
				key = list(self.spider_settings['logins'])[n]
				self.logger.debug("Using a random login information. Returning login for key : %s" % (key))
			
			self.login = self.spider_settings['logins'][key]
		
		return self.login


	def savestats(self):
		stat = ScrapeStat(scrape=self.scrape)

		stat.thread 			= self.dao.stats[Thread] if Thread in self.dao.stats else 0
		stat.message 			= self.dao.stats[Message] if Message in self.dao.stats else 0
		stat.message_propval 	= self.dao.stats[MessageProperty] if MessageProperty in self.dao.stats else 0
		stat.user 				= self.dao.stats[User] if User in self.dao.stats else 0
		stat.user_propval 		= self.dao.stats[UserProperty] if UserProperty in self.dao.stats else 0

		stat.request_sent = self.crawler.stats.get_value('downloader/request_count') or 0
		stat.request_bytes = self.crawler.stats.get_value('downloader/request_bytes') or 0
		stat.response_received = self.crawler.stats.get_value('downloader/response_count') or 0
		stat.response_bytes = self.crawler.stats.get_value('downloader/response_bytes') or 0
		stat.item_scraped = self.crawler.stats.get_value('item_scraped_count') or 0

		stat.save()

	def savestats_handler(self):
		self.savestat_taskid = None
		self.savestats()
		self.savestat_taskid = reactor.callLater(self.statsinterval, self.savestats_handler)


	


