import scrapy
from scrapy import signals
from peewee import *
from torforum_crawler.database.orm.models import *
from datetime import datetime
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
		self.indexmode=False
		self.settings = kwargs['settings']	# If we don't do that, the setting sobject only exist after __init()__

		self.load_spider_settings()
		self.initlogs()

		self.dao = DatabaseDAO(self, donotcache=[Message, UserProperty])
		self.set_timezone()

		try:
			self.forum = Forum.get(spider=self.name)
		except:
			raise Exception("No forum entry exist in the database for spider " + spider.name)

		self.dao.initiliaze(self.forum) # Will preload some data in the database for performance gain
		self.login = self.get_login()
		self.set_proxy()
		self.set_deltafromtime()
		self.set_deltamode()
		self.set_indexingmode()
		self.register_new_scrape()
		self.start_statistics()

	@classmethod
	def from_crawler(cls, crawler, *args, **kwargs):
		spider = cls(*args, settings = crawler.settings,**kwargs)
		spider.crawler = crawler
		return spider

	def closed( self, reason ):
		self.scrape.end = datetime.now();
		self.scrape.reason = reason
		self.scrape.save()

		if self.process_created:
			self.process.end = datetime.now()
			self.process.save()

		if self.savestat_taskid:
			self.savestat_taskid.cancel()
		self.savestats()
		
	#Check settings and database to figure wh
	def set_deltafromtime(self):
		self.lastscrape = Scrape.select().where(Scrape.forum == self.forum and Scrape.end.is_null(False) and Scrape.reason=='finished').order_by(Scrape.start.desc()).first()

		self.deltafromtime = None;	# When doing a delta scrape, use this time as a reference
		if 'deltafromtime' in self.settings:
			if isinstance(self.settings['deltafromtime'], str):
				self.deltafromtime = parser.parse(self.settings['deltafromtime'])
			elif isinstance(datetime, self.settings['deltafromtime']):
				self.deltafromtime = self.settings['deltafromtime']
			else:
				raise ValueError("Cannot interpret timezone %s" % str(self.settings['deltafromtime']))
		elif self.lastscrape:
			self.deltafromtime = self.lastscrape.start

	#Check settings and attributes to define if we do a Full or Delta crawl.
	def set_deltamode(self):
		self.deltamode = False
		if 'deltamode' in self.settings:
			self.deltamode = self.settings['deltamode']

		if not self.deltafromtime and self.deltamode == True:
			self.deltamode = False
			self.logger.warning("Delta crawl was requested, but no time reference is available. Switching to full crawl.")

		if self.deltamode == True:
			self.logger.info("Doing a delta crawl. Time reference is %s %s" % (str(self.deltafromtime), os.environ['TZ']))
		else:
			self.logger.info("Doing a full crawl")

		if self.deltamode == False:
			self.deltafromtime = None


	def set_indexingmode(self):
		self.indexingmode = False
		if 'indexingmode' in self.settings:
			self.indexingmode = self.settings['indexingmode']

	def initlogs(self):
		try:
			for logger_name in  self.settings['DISABLE_LOGGER'].split(','):
				logging.getLogger(logger_name).disabled=True
		except:
			pass

		try:
			colorformatter = ColorFormatterWrapper(self.logger.logger.parent.handlers[0].formatter)
			self.logger.logger.parent.handlers[0].setFormatter(colorformatter)
		except:
			pass

	def set_proxy(self):
		if not hasattr(self, 'proxy'):	# can be given by command line
			if 'PROXY' in self.settings:  # proxy is the one to use. Proxies is the definition.
				if 'PROXIES' in self.settings and self.settings['PROXY'] in self.settings['PROXIES']:
					self.proxy = self.settings['PROXIES'][self.settings['PROXY']]
				else:
					raise ValueError("Proxy %s does not exist in self.settings PROXIES " % self.settings['PROXY'])
			else:
				if 'PROXIES' in self.settings:
					if len(self.settings['PROXIES']) > 0:
						first = list(self.settings['PROXIES'])[0]
						self.proxy = self.settings['PROXIES'][first]

	def set_timezone(self):
		if 'timezone' in self.spider_settings:
			os.environ['TZ'] = self.spider_settings['timezone']	# Set environment timezone.
			time.tzset()
			db.set_timezone() # Sync db timezone with environment.

	def load_spider_settings(self):
		self.spider_settings = {}
		setting_module = "%s.%s.settings" % (self.settings['BOT_NAME'], self.name)
		try:
			self.spider_settings = import_module(setting_module).settings
		except:
			self.logger.warning("Cannot load spider specific settings from : %s" % setting_module)

	def register_new_scrape(self):
		self.process_created=False 	# Indicates that this spider created the process entry. Will be responsible of adding end date
		if not self.process:	# Can be created by a script and passed to the constructor
			self.process = Process()
			self.process.start = datetime.now()
			self.process.pid = os.getpid()
			self.process.cmdline = ' '.join(sys.argv)
			self.process.save()
			self.process_created = True

		self.scrape = Scrape();	# Create the new Scrape in the databse.
		self.scrape.start = datetime.now()
		self.scrape.process = self.process
		self.scrape.forum = self.forum
		self.scrape.deltamode = self.deltamode;
		self.scrape.deltafromtime = self.deltafromtime;
		self.scrape.indexingmode = self.indexingmode
		self.scrape.save();		

	def start_statistics(self):
		self.statsinterval = 30
		if 'statsinterval' in self.settings:
			self.statsinterval = int(self.settings['statsinterval'])

		self.savestat_taskid = reactor.callLater(self.statsinterval, self.savestats_handler)		

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
		if self.deltamode == False:
			return True
		else:
			val =self.isinvalidated(recordtime, dbrecordtime)
			if val:
				self.logger.debug('Record dated from %s is considered invalidated. Crawling' % (str(recordtime)))
			else:
				self.logger.debug('Record dated from %s is considered up to date. Do not crawl' % (str(recordtime)))

			return val


	def isinvalidated(self, recordtime=None, dbrecordtime=None):
		if not recordtime:
			return True
		else:
			if self.deltafromtime:
				return (self.deltafromtime < recordtime)
			else:
				if not dbrecordtime:
					return True
				else:
					return (dbrecordtime < recordtime)


	#Return the requested login information from the spier settings.
	# attribute "login" must be given (-a login="paramValue" using the CLI)
	# attribute can be a numerical index or the login dict key. If not specified, a random entry is returned
	def get_login(self):
		if not hasattr(self.__class__, 'taken_logins'):
			self.__class__.taken_logins = {}	# Initialise that

		if not hasattr(self, 'login') or isinstance(self.login, str) or isinstance(self.login, list):
			if 'logins' not in self.spider_settings:
				raise Exception("No login defined in spider settings")

			if len(self.spider_settings['logins']) == 0:
				raise Exception("Empty login list in spider settings")			

			logininput = None;
			if hasattr(self, 'login'):
				logininput = self.login
			elif 'login' in self.settings:
				logininput = self.settings['login']

			logindict = {}
			if isinstance(logininput, list):
				for k in logininput:
					if k in self.spider_settings['logins']:
						logindict[k] = self.spider_settings['logins'][k]
					else:
						raise ValueError("No login information with index %s" % k)
			else:
				logindict = self.spider_settings['logins'];

			if not logininput or isinstance(logininput, list):	#None or list
				key = self.pick_in_list(logindict.keys(), counts=self.__class__.taken_logins)
				self.logger.debug("Using a random login information. Returning login for key : %s" % (key))
				
			elif isinstance(logininput, str):
				if logininput not in logindict:
					raise ValueError("No login information with index : %s" % logininput)
				key = logininput
			else:
				raise ValueError("logininput is of unsupported type %s" % str(type(logininput))) # Should never happend
			
			self.login = logindict[key]

			if not key in self.__class__.taken_logins:
				self.__class__.taken_logins[key] = 0
			self.__class__.taken_logins[key] += 1

		return self.login

	def pick_in_list(self,items, counts=None):
		if len(items) == 0:
			raise ValueError("Cannot pick a value in an empty list")
		if not counts:
			n= random.randrange(0,len(items))
			return list(items)[n]

		for item in items:
			if item not in counts:
				counts[item] = 0

		count_min = None
		selected_key = None
		for k in counts:
			if counts[k]<count_min or count_min == None:
				count_min = counts[k]
				selected_key = k

		return selected_key
	

	def savestats(self):
		stat = ScrapeStat(scrape=self.scrape)

		stat.thread 			= self.dao.stats[Thread] if Thread in self.dao.stats else 0
		stat.message 			= self.dao.stats[Message] if Message in self.dao.stats else 0
		stat.message_propval 	= self.dao.stats[MessageProperty] if MessageProperty in self.dao.stats else 0
		stat.user 				= self.dao.stats[User] if User in self.dao.stats else 0
		stat.user_propval 		= self.dao.stats[UserProperty] if UserProperty in self.dao.stats else 0

		stat.request_sent 		= self.crawler.stats.get_value('downloader/request_count') or 0
		stat.request_bytes 		= self.crawler.stats.get_value('downloader/request_bytes') or 0
		stat.response_received 	= self.crawler.stats.get_value('downloader/response_count') or 0
		stat.response_bytes 	= self.crawler.stats.get_value('downloader/response_bytes') or 0
		stat.item_scraped 		= self.crawler.stats.get_value('item_scraped_count') or 0

		stat.save()

	def savestats_handler(self):
		self.savestat_taskid = None
		self.savestats()
		self.savestat_taskid = reactor.callLater(self.statsinterval, self.savestats_handler)

	def get_all_users_url(self):

		page = 1
		pagesize = 200;
		while False:
			userblock = User.select().where(User.forum == self.forum and User.relativeurl.is_null(False)).paginate(page, pagesize)
			for user in userblock:
				yield self.make_url(user.relativeurl)
			if len(userblock) < pagesize:
				break;
			page += 1





	


