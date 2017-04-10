import scrapy
from scrapy import signals
from peewee import *
from scrapyprj.database.forums.orm.models import *
from datetime import datetime
from scrapyprj.database.settings import forums as dbsettings
from scrapyprj.database.dao import DatabaseDAO
from scrapyprj.database import db
from scrapyprj.spiders.BaseSpider import BaseSpider

from fake_useragent import UserAgent
import os, time, sys
from dateutil import parser
import random
from scrapy import signals
from Queue import Queue
import itertools as it


from twisted.internet import reactor

class ForumSpider(BaseSpider):
	user_agent  = UserAgent().random
	def __init__(self, *args, **kwargs):
		super(ForumSpider, self).__init__( *args, **kwargs)

		db.init(dbsettings)
		self.dao = DatabaseDAO(cacheconfig='forums', donotcache=[Message, UserProperty])	# Save some RAM. We usually don't have to read these object form the DB, just write.
		self.set_timezone()

		try:
			self.forum = Forum.get(spider=self.name)
		except:
			raise Exception("No forum entry exist in the database for spider " + self.name)

		self.dao.cache.reload(User, User.forum == self.forum)
		self.dao.cache.reload(Thread, Thread.forum == self.forum)

		self.set_deltafromtime()
		self.set_deltamode()
		self.configure_thread_indexing()
		self.set_itemtocrawl()
		self.register_new_scrape()
		self.start_statistics()

	@classmethod
	def from_crawler(cls, crawler, *args, **kwargs):
		spider = cls(*args, settings = crawler.settings,**kwargs)
		spider.crawler = crawler
		crawler.signals.connect(spider.spider_closed, signal=signals.spider_closed)
		crawler.signals.connect(spider.spider_idle, signal=signals.spider_idle)			# We will fetch some users/thread that we need to re-read from the database.

		return spider


	def count_total_indexed_thread(self):
		cls = self.__class__
		if not hasattr(cls, '_remaining_indexed_thread_counter'):
			cls._remaining_indexed_thread_counter = None

		if not cls._remaining_indexed_thread_counter:
			cls._remaining_indexed_thread_counter = Thread.select(fn.count(1).alias('n')).where(Thread.scrape == self.indexingscrape).get().n

		return cls._remaining_indexed_thread_counter

	def count_known_user(self):
		cls = self.__class__
		if not hasattr(cls, '_total_known_user'):
			cls._total_known_user = None
		if not cls._total_known_user:
			cls._total_known_user = User.select(fn.count(1).alias('n')).where(User.relativeurl.is_null(False) and ~(User.scrape << (Scrape.select(User.id).where(Scrape.process == self.process)))).get().n

		return cls._total_known_user

	# When Spider is idle, this callback is called.
	def spider_idle(self, spider):
		spider.logger.debug("IDLE")
		thread_qty = 25
		user_qty = 300
		donethread= True

		if not hasattr(self.__class__, 'thread_poped'):
			self.__class__.thread_poped=  0

		if not hasattr(self.__class__, 'user_poped'):
			self.__class__.user_poped=  0

		if self.should_use_already_scraped_threads():
			spider.logger.info("%s known threads crawled on a total of %s. Consuming %s from queue." % (self.__class__.thread_poped, self.count_total_indexed_thread(), thread_qty))
			for req in self.generate_thread_request(thread_qty):
				self.__class__.thread_poped += 1
				donethread = False
				self.crawler.engine.crawl(req, spider)

		if donethread and self.should_use_already_scraped_threads():
			spider.logger.info("%s known users crawled on a total of %s. Consuming %s from queue." % (self.__class__.user_poped, self.count_known_user(), user_qty))
			for req in self.generate_user_request(user_qty):
				self.__class__.user_poped += 1
				self.crawler.engine.crawl(req, spider)

	# When Idle, will read threads from indexer
	def generate_thread_request(self, n):
		return map(lambda x: self.make_thread_request (x), it.islice(self.consumethreads(), n)) # Reads n Thread from the Queue and convert them to request

	#When Idle, will refresh known users.
	def generate_user_request(self, n):
		return map(lambda x: self.make_user_request (x), it.islice(self.consume_users(), n)) # Reads n Thread from the Queue and convert them to request

	# Set the right option to correctly handle multiple instances of spiders. 
	# First a spider is launched in indexingmode, then many instance read that the first indexer found.
	def configure_thread_indexing(self):
		if not hasattr(self.__class__, '_threadqueue'):
			self.__class__._threadqueue = Queue()
		
		if not hasattr(self, 'indexingscrape'):
			self.indexingscrape = None

		if not hasattr(self, 'indexingmode'):
			self.indexingmode = False
			if 'indexingmode' in self.settings:
				if isinstance(self.settings['indexingmode'], str):
					self.indexingmode = True if self.settings['indexingmode'] == 'True' else False
				elif isinstance(self.settings['indexingmode'], bool):
					self.indexingmode = self.settings['indexingmode']
				else:
					raise ValueError('Setting indexingmode is of unsupported type %s ' % (str(type(self.settings['indexingmode']))))

			if not hasattr(self.__class__, '_total_thread_count' ):
				self.__class__._total_thread_count = None



	def should_use_already_scraped_threads(self):
		if self.indexingmode == True:	# Scraping now, not already scraped.
			return False

		if self.indexingscrape == None:	# Will happen if launched from scrapy command line and not crawler script
			return False

		return True

	def consumethreads(self):	# Generator reading indexed thread by chunks
		pagesize = 5000
		queue = self.__class__._threadqueue

		if self.indexingmode:
			self.logger.error("Trying to read thread previously indexed, but we actually are in indexing mode.")

		if not self.indexingscrape:
			self.logger.error("Trying to read thread previously indexed, but no scrape ID used dureing indexing is available.")
		
		if not hasattr(self.__class__, '_thread_pageindex'):
			self.__class__._thread_pageindex=1
		
		while True:
			if queue.empty():
				self.logger.debug("Reading a page of already indexed threads.")

				thread_page = Thread.select().where(Thread.scrape == self.indexingscrape).paginate(self.__class__._thread_pageindex, pagesize)
				self.__class__._thread_pageindex += 1
				self.logger.debug("Got %s threads" % str(len(thread_page)))

				if len(thread_page) == 0:
					return 

				for thread in thread_page:
					queue.put(thread)


			while not queue.empty():
				yield queue.get()

	def consume_users(self):	# Generator reading already known users by chunks
		pagesize = 5000

		if not hasattr(self.__class__, '_userqueue'):
			self.__class__._userqueue = Queue()

		queue = self.__class__._userqueue

		
		if not hasattr(self.__class__, '_user_pageindex'):
			self.__class__._user_pageindex=1
		
		while True:
			if queue.empty():
				self.logger.debug("Reading a page of users")
				user_page = User.select().where(User.relativeurl.is_null(False) and ~(User.scrape << (Scrape.select(User.id).where(Scrape.process == self.process)))).paginate(self.__class__._user_pageindex, pagesize)
				self.__class__._user_pageindex += 1
				self.logger.debug("Got %s users" % str(len(user_page)))

				if len(user_page) == 0:
					return 

				for user in user_page:
					queue.put(user)


			while not queue.empty():
				yield queue.get()

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
		
	#Check settings and database to figure wh
	def set_deltafromtime(self):
		self.lastscrape = Scrape.select().where(Scrape.forum == self.forum and Scrape.end.is_null(False) and Scrape.reason=='finished').order_by(Scrape.start.desc()).first()	# todo, user first of last process

		self.deltafromtime = None;	# When doing a delta scrape, use this time as a reference
	
		if 'deltafromtime' in self.settings and self.settings['deltafromtime']:
			if isinstance(self.settings['deltafromtime'], str):
				self.deltafromtime = self.to_utc(parser.parse(self.settings['deltafromtime']))
			elif isinstance(datetime, self.to_utc(self.settings['deltafromtime'])):
				self.deltafromtime = self.settings['deltafromtime']
			else:
				raise ValueError("Cannot interpret deltafromtime %s" % str(self.settings['deltafromtime']))
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
			self.logger.info("Doing a delta crawl. Time reference is %s %s" % (str(self.deltafromtime), str(self.timezone)))
		else:
			self.logger.info("Doing a full crawl")

		if self.deltamode == False:
			self.deltafromtime = None


	def set_itemtocrawl(self):
		allitems = ['message', 'user', 'thread']
		if not hasattr(self, 'itemtocrawl'):
			self.itemtocrawl = allitems

		if 'itemtocrawl' in self.settings:
			if isinstance(self.settings['itemtocrawl'], str):
				self.itemtocrawl = 	self.settings['itemtocrawl'].split(',')
			else:
				self.itemtocrawl = allitems

		if self.indexingmode:
			self.itemtocrawl = ['thread']

		if self.should_use_already_scraped_threads():
			self.itemtocrawl.remove('thread')



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

		self.scrape 				= Scrape();	# Create the new Scrape in the databse.
		self.scrape.start 			= datetime.utcnow()
		self.scrape.process 		= self.process
		self.scrape.forum 			= self.forum
		self.scrape.deltamode 		= self.deltamode;
		self.scrape.deltafromtime 	= self.deltafromtime;
		self.scrape.indexingmode 	= self.indexingmode
		self.scrape.login 			= self._loginkey
		self.scrape.proxy 			= self._proxy_key
		self.scrape.save();		


	def start_statistics(self):
		self.statsinterval = 30
		if 'statsinterval' in self.settings:
			self.statsinterval = int(self.settings['statsinterval'])

		self.savestats_handler()	


	# Tell if the spider should make a request r not depending on : 1) Type of record, 2) Date of record.
	def shouldcrawl(self, item, recordtime=None, dbrecordtime=None):
		if item not in self.itemtocrawl:
			return False

		if isinstance(recordtime, str):
			recordtime = self.to_utc(parser.parse(recordtime))		

		if isinstance(dbrecordtime, str):
			dbrecordtime = self.to_utc(parser.parse(dbrecordtime))	

		if self.deltamode == False:
			return True
		else:
			val =self.isinvalidated(recordtime, dbrecordtime)
			if val:
				self.logger.debug('Record dated from %s is considered invalidated. Crawling' % (str(recordtime)))
			else:
				self.logger.debug('Record dated from %s is considered up to date. Do not crawl' % (str(recordtime)))

			return val

	# Tell if a dated item is outdated and need to be rescraped from the site.
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


	def savestats(self):
		stat = ScrapeStat(scrape=self.scrape)

		stat.thread 			= self.dao.stats[Thread] 			if Thread 			in self.dao.stats else 0
		stat.message 			= self.dao.stats[Message] 			if Message 			in self.dao.stats else 0
		stat.message_propval 	= self.dao.stats[MessageProperty] 	if MessageProperty 	in self.dao.stats else 0
		stat.user 				= self.dao.stats[User] 				if User 			in self.dao.stats else 0
		stat.user_propval 		= self.dao.stats[UserProperty] 		if UserProperty 	in self.dao.stats else 0

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
