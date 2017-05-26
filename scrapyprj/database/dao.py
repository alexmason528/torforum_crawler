import scrapyprj.database.db as db
from peewee import *
from scrapyprj.database.cache import Cache
from scrapy import crawler
from scrapyprj.database.orm import *
import logging
import inspect
import traceback
import scrapyprj.database.forums.orm.models as forum_models
import scrapyprj.database.markets.orm.models as market_models
from IPython import embed
from scrapy.exceptions import CloseSpider


# This object is meant to stand between the application and the database.
# The reason of its existence is :
# 	- Centralized pre-insert, pre-read operation (monkey patch as well)
# 	- Ease to use of a cache with the ORM.

class DatabaseDAO:

	# This config list unique keys which we can use as cache key.
	cache_configs = {
		'forums' : {
			forum_models.Thread				: ('forum', 'external_id'),	
			forum_models.User 				: ('forum', 'username'),
			forum_models.CaptchaQuestion 	: ('forum', 'hash'),
			forum_models.Message 			: ('forum', 'external_id')	
		},
		'markets' : {
			market_models.Ads 				: ('market', 'external_id'),	
			market_models.User 				: ('market', 'username'),
			market_models.CaptchaQuestion 	: ('market', 'hash'),
			market_models.AdsFeedback 		: ('ads', 'hash'),
			market_models.SellerFeedback 	: ('seller', 'hash')
		}
	}

	def __init__(self, cacheconfig, donotcache = []):
		if cacheconfig not in self.cache_configs:
			raise ValueError("%s is not a valid cache config" % cacheconfig)

		self.queues = {}
		self.cache = Cache(self.cache_configs[cacheconfig])
		self.config =  {
			'dependencies' : {},
			'callbacks' : {}
		}
		self.stats = {}
		self.queuestats = {}

		self._donotcache = donotcache
		self.logger = logging.getLogger('DatabaseDAO')

	#Make a model queue flush when before another
	def add_dependencies(self, model, deps_list):	
		self.assertismodelclass(model)

		self.config['dependencies'][model] = []
		for deps in deps_list:
			self.assertismodelclass(deps)
			self.config['dependencies'][model].append(deps)

	def get_dependencies(self, model):
		self.assertismodelclass(model)
		if model not in self.config['dependencies']:
			self.config['dependencies'][model] = []
		return  self.config['dependencies'][model]

	def initiliaze(self, forum):
		pass


	def enable_cache(self, typelist):
		for modeltype in typelist:
			if modeltype in self._donotcache:
				self._donotcache.remove(modeltype)

	def disable_cache(self, typelist):
		for modeltype in typelist:
			if modeltype not in self._donotcache:
				self._donotcache.append(modeltype)

	#Add a callback on a queue before/after flush is done
	def before_flush(self, modeltype, callback, *args, **kwargs):
		self.add_callback('before_flush', modeltype, callback, *args, **kwargs)

	def after_flush(self, modeltype, callback):
		self.add_callback('after_flush', modeltype, callback, *args, **kwargs)

	#Register a callback. They are called explicitly later
	def add_callback(self,  name, modeltype, callback, *args, **kwargs):
		self.assertismodelclass(modeltype)

		if name not in self.config['callbacks']:
			self.config['callbacks'][name] = {}

		if modeltype not in self.config['callbacks'][name]:
			self.config['callbacks'][name][modeltype] = []

		data_struct = {
			'callback' : callback,
			'args' : list(args),
			'kwargs' : kwargs
		}

		self.config['callbacks'][name][modeltype].append(data_struct)

	#Exceute a list of callback and passes output to input of the next like a pipeline as well as args of exec_callback.
	def exec_callbacks(self, name, modeltype, *args, **kwargs):
		if name not in self.config['callbacks']:
			return args[0] if len(args) == 1 else args

		if modeltype not in self.config['callbacks'][name]:
			return args[0] if len(args) == 1 else args

		pipeline_args = list(args)
		for callback_data in self.config['callbacks'][name][modeltype]:
			merged_args = callback_data['args'] + pipeline_args
			merged_kwargs = callback_data['kwargs'].copy()
			merged_kwargs.update(kwargs)
			last_pipeline_args = pipeline_args
			result = callback_data['callback'].__call__(*merged_args, **merged_kwargs)

			if result == None: 
				pipeline_args = []
			elif isinstance(result, tuple):
				pipeline_args = list(result)
			else:
				pipeline_args = [result]


			if len(pipeline_args) != len(last_pipeline_args):
				raise RuntimeError('Callback %s for model %s did not returned as much data as its input. Returned %d, expected : %d' % (name, modeltype.__name__, len(pipeline_args), len(last_pipeline_args)))

		return result

	# Add a peewee model to a queue
	def enqueue(self, obj, spider=None):
		self.assertismodelclass(obj.__class__)
		if isinstance(obj, BasePropertyOwnerModel):
			obj._extra_data['spider'] = spider
		queuename = obj.__class__.__name__
		if queuename not in self.queues:
			self.queues[queuename] = []
		self.queues[queuename].append(obj)

		if queuename not in self.queuestats:
			self.queuestats[queuename] = {}
		
		if spider not in self.queuestats[queuename]:
			self.queuestats[queuename][spider] = 0

		self.queuestats[queuename][spider] += 1

	#Gives an object just like peewee.get does, but look into the cache first
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

		#if self.enablecache:
		self.cache.write(obj)
		return obj

	# just like peewee.get_or_create but look in the cache first
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

		#If we try to flush a model that is dependent on another, flush the dependenciy first.
		for deps in self.get_dependencies(modeltype):
			self.flush(deps)

		queue = self.queues[modeltype.__name__]
		queue = self.exec_callbacks('before_flush', modeltype, queue)

		requireCloseSpider = False
		msg = ''
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
						success = False
						requireCloseSpider = True

			if success:
				#Hooks
				self.exec_callbacks('after_flush', modeltype, queue)

				#Stats
				queuename = modeltype.__name__
				if queuename in self.queuestats:
					for spider in self.queuestats[queuename]:

						if spider not in self.stats:
							self.stats[spider] = {}

						if modeltype not in self.stats[spider]:
							self.stats[spider][modeltype] = 0

						self.stats[spider][modeltype] += self.queuestats[queuename][spider]		# consume stats for spider
						self.queuestats[queuename][spider] = 0									# reset to 0
				
				#cache
				self.cache.bulkwrite(queue)
				reloadeddata = self.cache.reloadmodels(queue, queue[0]._meta.primary_key)	# Retrieve primary key (autoincrement id)
				#Propkey/propval
				if issubclass(modeltype, BasePropertyOwnerModel):	# Our class has a property table defined (propkey/propval)
					if reloadeddata and len(reloadeddata) > 0:
						for obj in reloadeddata:
							obj_spider = obj._extra_data['spider'] 
							props = obj.getproperties()
							for prop in props:
								self.enqueue(prop, obj_spider)

						self.flush(modeltype._meta.valmodel, donotcache)	# Flush db properties

				#Remove data from cache if explicitly asked not to cache. That'll save some memory
				# We delete after inserting instead of simply preventing because we want BasePropertyOwnerModel
				# object to successfully respect foreign key constraints with Auto Increment fields.
				if donotcache:
					self.cache.bulkdeleteobj(reloadeddata)	

		self.queues[modeltype.__name__] = []

		if requireCloseSpider:
			raise CloseSpider(msg)

	#Monkey patch to handle peewee's limitation for MySQL "On duplicate key update" close.
	def add_onduplicate_key(self, q, fields):
		sql = q.sql();
		return (sql[0] + " on duplicate key update " + ','.join(map(lambda v: v.db_column+"=values(%s)" % v.db_column, fields.values())), sql[1])

	def assertismodelclass(self, modeltype):
		if not inspect.isclass(modeltype):
			raise Exception("Type must be a Class. Got %s" % modeltype.__class__.__name__)
		elif not issubclass(modeltype, Model):
			raise Exception("Given type must be a subclass of PeeWee.Model. Got %s" % modeltype.__name__)

	def dumpqueue(self, filename, queue):
		try:
			with open(filename, 'w+') as f:	
				for obj in queue:
					f.write(str(obj._data))
		except:
			pass

	def get_stats(self, spider=None):
		if spider not in self.stats:
				self.stats[spider] = {}

		return self.stats[spider]