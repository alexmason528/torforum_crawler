from torforum_crawler.database.orm.models import *
import torforum_crawler.database as database
import inspect
from peewee import *
from scrapy.conf import settings


# This object is meant to stand between the application and the database.
# The reason of its existence is :
# 	- Centralized pre-insert, pre-read operation (monkey patch as well)
# 	- Ease to use of a cache with the ORM.
# One instance of MArshall should be use per spider.	
class Marshall:

	def __init__(self, spider):

		self.users = {}
		self.threads = {}
		self.queues = {}


		self.spider = spider
		self.cache = {}
		self.cachekey = {
			'Thread' : 'externam_id',
			'User' : 'username',
			'CaptchaQuestion' : 'hash'
		}

		self.q= list()

		db.init(settings['DATABASE']); 

		try:
			self.forum = Forum.get(spider=spider.name)
		except:
			raise Exception("No forum entry exist in the database for spider " + spider.name)

		# First round to gather all existing users and threads.
		# Will reduce significantly exchange with database.
		self.reloadcache(User, User.forum == self.forum)
		self.reloadcache(Thread, Thread.forum == self.forum)


	def add(self, obj):
		self.assertismodelclass(obj.__class__)
		queuename = obj.__class__.__name__
		if queuename not in self.queues:
			self.queues[queuename] = []
		self.queues[queuename].append(obj)


	def get_or_create(self, modeltype, *args, **kwargs):
		self.assertismodelclass(modeltype)
		self.initcache_ifnotexist(modeltype)
		modelname = modeltype.__name__
		key = self.getcachekey(modeltype)
		if key in self.cache[modelname]:
			return self.cache[modelname][key]
		else:
			obj, created = modeltype.get_or_create(**kwargs)
			self.cache[modelname][key] = obj
			if created :
				self.spider.logger.debug("Created new " + modelname + " with key : " + key)
			return obj


	def initcache_ifnotexist(self, modeltype):
		if not modeltype.__name__ in self.cache:
			self.cache[modeltype.__name__] = {}

	def getcachekey(self, modeltype):
		self.assertismodelclass(modeltype)
		if modeltype.__name__ in self.cachekey:
			return self.cachekey[modeltype.__name__]
		else:
			pk = modeltype._meta.primary_key.name
			self.spider.logger.debug('Accessing cache key for ' + modeltype.__name__ + " and no key defined. Defaulting on primary key : " + pk)
			self.cachekey[modeltype.__name__] = pk
			return pk

	def reloadcache(self, modeltype, whereclause):
		self.assertismodelclass(modeltype)
		self.initcache_ifnotexist(modeltype)

		objects = modeltype.select().where(whereclause)
		cachekey = self.getcachekey(modeltype)
		for obj in objects:
			self.cache[modeltype.__name__][cachekey] = obj


	def flush(self, modeltype):
		self.assertismodelclass(modeltype)
		chunksize = 100
		if modeltype.__name__ not in self.queues:
			self.spider.logger.debug("Trying to flush a queue of "+ modeltype.__name__ +" that has never been filled before.")
			return

		queue = self.queues[modeltype.__name__]
		
		if len(queue) > 0 :
			with database.db.proxy.atomic():
				data = list(map(lambda x: (x._data) , queue)) # Extract a list of dict from our Model queue
				for idx in range(0, len(data), chunksize):
					q = modeltype.insert_many(data[idx:idx+chunksize])
					sql = self.add_onduplicate_key(q, modeltype._meta.fields)  # Manually add "On duplicate key update"
					db.proxy.execute_sql(sql[0], sql[1])
				
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