from torforum_crawler.database.orm.models import *
import torforum_crawler.database.db as db
import inspect
from peewee import *
from scrapy.conf import settings
from torforum_crawler.database.cache import Cache
from scrapy import crawler
import traceback
import logging
from IPython import embed

# This object is meant to stand between the application and the database.
# The reason of its existence is :
# 	- Centralized pre-insert, pre-read operation (monkey patch as well)
# 	- Ease to use of a cache with the ORM.
# One instance of DatabaseDAO should be use per spider.	
class DatabaseDAO:

	def __init__(self, spider,donotcache = []):

		self.queues = {}
		self.spider = spider
		self.cache = Cache()
		self.stats = {}

		self._donotcache = donotcache
		self.logger = logging.getLogger('DatabaseDAO')

		db.init(settings['DATABASE']);

	def initiliaze(self, forum):
		# First round to gather all existing users and threads.
		# Will reduce significantly exchange with database.
		#if self.enablecache:
		self.cache.reload(User, User.forum == forum)
		self.cache.reload(Thread, Thread.forum == forum)

	def enable_cache(self, typelist):
		for modeltype in typelist:
			if modeltype in self._donotcache:
				self._donotcache.remove(modeltype)

	def disable_cache(self, typelist):
		for modeltype in typelist:
			if modeltype not in self._donotcache:
				self._donotcache.append(modeltype)


	def enqueue(self, obj):
		self.assertismodelclass(obj.__class__)
		queuename = obj.__class__.__name__
		if queuename not in self.queues:
			self.queues[queuename] = []
		self.queues[queuename].append(obj)

	def get(self, modeltype, *args, **kwargs):
		#if self.enablecache:
		cachedval = self.cache.readobj(modeltype(**kwargs))	# Create an object 

		if cachedval:
			self.logger.debug("Cache hit : Read %s with params %s" %( modeltype.__name__, str(kwargs)))
			return cachedval
		else:
			self.logger.debug("Cache miss for %s with params %s " % (modeltype.__name__, str(kwargs) ))

		#todo : Get properties for BasePropertyOwnerModel
		obj = modeltype.get(**kwargs)

		if self.enablecache:
			self.cache.write(obj)
		return obj

	def get_or_create(self, modeltype, **kwargs):
		#if self.enablecache:
		cached_value = self.cache.readobj(modeltype(**kwargs))

		if cached_value:
			self.logger.debug("Cache hit : Read %s with params %s " % (modeltype.__name__, str(kwargs)) )
			return cached_value
		else:
			self.logger.debug("Cache miss for %s with params %s " % (modeltype.__name__, str(kwargs)) )

		#todo : Get properties for BasePropertyOwnerModel
		with db.proxy.atomic():
			obj, created = modeltype.get_or_create(**kwargs)
		#if self.enablecache:
		self.cache.write(obj)
		return obj

	# Bulk insert a batch of data within a queue
	def flush(self, modeltype, donotcache = False):

		donotcache = donotcache or modeltype in self._donotcache

		self.assertismodelclass(modeltype)
		chunksize = 100
		if modeltype.__name__ not in self.queues:
			self.logger.debug("Trying to flush a queue of %s that has never been filled before." % modeltype.__name__ )
			return

		queue = self.queues[modeltype.__name__]

		success = True
		if len(queue) > 0 :
			with db.proxy.atomic():
				for idx in range(0, len(queue), chunksize):
					queue_chunked = queue[idx:idx+chunksize]
					data = list(map(lambda x: (x._data) , queue_chunked)) # Extract a list of dict from our Model queue
					q = modeltype.insert_many(data)
					updateablefields = {}
					for fieldname in modeltype._meta.fields:
						field = modeltype._meta.fields[fieldname]
						if not isinstance(field, PrimaryKeyField):
							updateablefields[fieldname] = field

					try:
						sql = self.add_onduplicate_key(q, updateablefields)  # Manually add "On duplicate key update"
						db.proxy.execute_sql(sql[0], sql[1])

					except Exception as e:	#We have a nasty error. Dumps useful data to a file.
						filename = "%s_queuedump.txt" % (modeltype.__name__)
						msg = "%s : Flushing %s data failed. Dumping queue data to %s.\nError is %s." % (self.__class__.__name__, modeltype.__name__, filename, str(e))
						self.logger.error("%s\n %s" % (msg, traceback.format_exc()))
						self.dumpqueue(filename, queue)
						self.spider.crawler.engine.close_spider(self.spider, msg)
						success = False

			if success:
				if modeltype not in self.stats:
					self.stats[modeltype] = 0
				self.stats[modeltype] += len(queue)
				
				self.cache.bulkwrite(queue)
				reloadeddata = self.cache.reloadmodels(queue, queue[0]._meta.primary_key)	# Retrieve primary key (autoincrement id)
				
				if issubclass(modeltype, BasePropertyOwnerModel):	# Our class has a property table defined (propkey/propval)
					if reloadeddata and len(reloadeddata) > 0:
						for obj in reloadeddata:
							props = obj.getproperties()
							for prop in props:
								self.enqueue(prop)

						self.flush(modeltype._meta.valmodel, donotcache)	# Flush db properties

				#Remove data from cache if explicitly asked not to cache. That'll save some memory
				# We delete after inserting instead of simply preventing because we want BasePropertyOwnerModel
				# object to successfully respect foreign key constraints with Auto Increment fields.
				if donotcache:
					self.cache.bulkdeleteobj(reloadeddata)	

		self.queues[modeltype.__name__] = []

	#Monkey patch to handle peewee's limitation for MySQL "On duplicate key update" close.
	def add_onduplicate_key(self, q, fields):
		sql = q.sql();
		return (sql[0] + " on duplicate key update " + ','.join(map(lambda v: v.db_column+"=values("+v.db_column+")", fields.values())), sql[1])

	def assertismodelclass(self, modeltype):
		if not inspect.isclass(modeltype):
			raise Exception("Type must be a Class")
		elif not issubclass(modeltype, Model):
			raise Exception("Given type must be a subclass of PeeWee.Model")

	def dumpqueue(self, filename, queue):
		try:
			with open(filename, 'w+') as f:	
				for obj in queue:
					f.write(str(obj._data))
		except:
			pass