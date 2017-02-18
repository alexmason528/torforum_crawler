from torforum_crawler.database.orm.models import *
import torforum_crawler.database.db as db
import inspect
from peewee import *
from scrapy.conf import settings
from torforum_crawler.database.cache import Cache


# This object is meant to stand between the application and the database.
# The reason of its existence is :
# 	- Centralized pre-insert, pre-read operation (monkey patch as well)
# 	- Ease to use of a cache with the ORM.
# One instance of Marshall should be use per spider.	
class Marshall:

	def __init__(self, spider):

		self.queues = {}
		self.spider = spider
		self.cache = Cache()
		try: 
			self.enablecache = settings['MARSHAL']['enablecache']
		except:
			self.enablecache = True

		db.init(settings['DATABASE']); 

		try:
			self.forum = Forum.get(spider=spider.name)
		except:
			raise Exception("No forum entry exist in the database for spider " + spider.name)

		# First round to gather all existing users and threads.
		# Will reduce significantly exchange with database.
		if self.enablecache:
			self.cache.reload(User, User.forum == self.forum)
			self.cache.reload(Thread, Thread.forum == self.forum)

	def add(self, obj):
		self.assertismodelclass(obj.__class__)
		queuename = obj.__class__.__name__
		if queuename not in self.queues:
			self.queues[queuename] = []
		self.queues[queuename].append(obj)

	def get(self, modeltype, *args, **kwargs):
		if self.enablecache:
			cachedval = self.cache.readobj(modeltype(**kwargs))	# Create an object 
  #   			import pdb; pdb.set_trace() 

			if cachedval:
				self.spider.logger.debug("Cache hit : Read " + modeltype.__name__ + " with params " + str(kwargs))
				return cachedval
			else:
				self.spider.logger.debug("Cache miss for " + modeltype.__name__ + " with params " + str(kwargs))

		return modeltype.get(**kwargs)

	def get_or_create(self, modeltype, **kwargs):
		if self.enablecache:
			cached_value = self.cache.readobj(modeltype(**kwargs))

			if cached_value:
				self.spider.logger.debug("Cache hit : Read " + modeltype.__name__ + " with params " + str(kwargs))
				return cached_value
			else:
				self.spider.logger.debug("Cache miss for " + modeltype.__name__ + " with params " + str(kwargs))

		
		obj, created = modeltype.get_or_create(**kwargs)
		if self.enablecache:
			self.cache.write(obj)
		return obj


	def flush(self, modeltype):
		self.assertismodelclass(modeltype)
		chunksize = 100
		if modeltype.__name__ not in self.queues:
			self.spider.logger.debug("Trying to flush a queue of "+ modeltype.__name__ +" that has never been filled before.")
			return

		queue = self.queues[modeltype.__name__]

		if len(queue) > 0 :
			with db.proxy.atomic():
				data = list(map(lambda x: (x._data) , queue)) # Extract a list of dict from our Model queue
				for idx in range(0, len(data), chunksize):
					q = modeltype.insert_many(data[idx:idx+chunksize])
					updateablefields = {}
					for fieldname in modeltype._meta.fields:
						field = modeltype._meta.fields[fieldname]
						if not isinstance(field, PrimaryKeyField):
							updateablefields[fieldname] = field
							
					sql = self.add_onduplicate_key(q, updateablefields)  # Manually add "On duplicate key update"
					db.proxy.execute_sql(sql[0], sql[1])


			if self.enablecache:
				self.cache.bulkwrite(queue)
				self.cache.reloadmodels(queue, queue[0]._meta.primary_key)	# Retrieve primary key (autoincrement id)
				
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