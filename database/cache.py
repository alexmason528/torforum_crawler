from torforum_crawler.database.orm.models import *
import torforum_crawler.database as database
import inspect
from peewee import *
from scrapy import settings

class Cache:

	# We can force the cache to use a specific key. Otherwise it finds what key to use searching for unique index first, then primary key.
	# Exmaples in comments. 
	cachekey = {
		'Thread' : ('forum', 'external_id'),	
		'User' : ('forum', 'username'),
		'CaptchaQuestion' : ('forum', 'hash'),
		'Message' : ('forum', 'external_id')	
	}

	def __init__(self):
		self.cachedata = {}

	def unsafewrite(self, obj):
		fieldname, cacheid = self.getcacheid(obj)
		if not cacheid:
			raise ValueError("Cannot write to cache object of type "  + obj.__class__.__name__ + " no usable id to identify the record.")
		self.cachedata[obj.__class__.__name__][cacheid] = obj

	def unsaferead(self, modeltype, cacheid):
		if cacheid in self.cachedata[modeltype.__name__]:
			if cacheid in self.cachedata[modeltype.__name__]:
				return self.cachedata[modeltype.__name__][cacheid]

	# For a specific Model, returns the unique key used to cache the object.
	# return (fieldname, cacheid) 
	# fieldname is the name of the field used as a key. Can be a string for single key or a tuple for composite key
	# cacheid is the value used as the index in the cache. Can be anything (literal, string, tuple)

	def getcacheid(self,obj):
		objclass = obj.__class__
		self.assertismodelclass(objclass)
		if objclass.__name__ in self.cachekey:
			fieldname = self.cachekey[objclass.__name__]
			cacheid = self.read_index_value(obj, fieldname)
			return (fieldname, cacheid)

		unique_idx = []
		for idx in objclass._meta.indexes:
			if idx[1] == True: # unique
				unique_idx.append(idx[0])
		if objclass._meta.primary_key:
			unique_idx.append(objclass._meta.primary_key.name)

		for fieldname in unique_idx:
			cacheid = self.read_index_value(obj, fieldname)
			if cacheid:
				return (fieldname, cacheid)
	
	def read_index_value(self, obj, idx):
		if isinstance(idx, tuple):	# we are dealing with a composite key
			complete = True
			keyval = tuple()
			for idx in idx :
				if idx in obj._data:
					keyval += (obj._data[idx],)	# Append to tuple
				else:
					complete  = False
					break
			return keyval if complete else None 
		elif isinstance(idx, str): 		# Single key
			if idx in obj._data:
				return obj._data[idx]



	def read(self, modeltype, keyval):
		self.assertismodelclass(modeltype)
		self.init_ifnotexist(modeltype)
		return self.unsaferead(modeltype, keyval)		

	def write(self, obj):
		self.assertismodelclass(obj.__class__)
		self.init_ifnotexist(obj.__class__)
		self.unsafewrite(obj)

	def bulkwrite(self, objlist):
		for obj in objlist: 
			self.assertismodelclass(obj.__class__)
			self.init_ifnotexist(obj.__class__)				
			self.unsafewrite(obj)

	def init_ifnotexist(self, modeltype):
		if not modeltype.__name__ in self.cachedata:
			self.cachedata[modeltype.__name__] = {}
	
	def reload(self, modeltype, whereclause):
		self.assertismodelclass(modeltype)
		self.init_ifnotexist(modeltype)
		objects = modeltype.select().where(whereclause)
		for obj in objects:
			self.unsafewrite(obj)

	def assertismodelclass(self, modeltype):
		if not inspect.isclass(modeltype):
			raise Exception("Type must be a Class")
		elif not issubclass(modeltype, Model):
			raise Exception("Given type must be a subclass of PeeWee.Model")

	def reloadmodels(self, objlist):
		objtype = None
		chunksize = 100
		cacheid_per_fieldname = {}
		if len(objlist) > 0 :
			modeltype = objlist[0].__class__
			fieldname, cacheid = self.getcacheid(objlist[0])
			for obj in objlist:
				self.assertismodelclass(obj.__class__)			
				objtype = obj.__class__ if not objtype else objtype
				if obj.__class__ != objtype:
					raise ValueError("Trying to reload partial set of data of different type.")
				
				fieldname, cacheid = self.getcacheid(obj)
				if fieldname not in cacheid_per_fieldname:
					cacheid_per_fieldname[fieldname] = []
				cacheid_per_fieldname[fieldname].append(cacheid)
			for fieldname in cacheid_per_fieldname.keys():
				cacheidlist = cacheid_per_fieldname[fieldname]
				for idx in range(0, len(cacheidlist), chunksize):
					data = cacheidlist[idx:idx+100]
					if isinstance(fieldname, str): #single key
						self.reload(modeltype, modeltype._meta.fields[fieldname] << data)

					elif isinstance(fieldname, tuple): # composite key. Peewee doesn't support that easily, we have to do some manual work
						whereclause = '('+','.join(map(lambda x: "`%s`" % x, fieldname))+')'  # (`col1`, `col2`)
						whereclause += " in (" + ','.join(map(lambda entry: '('+','.join(map(lambda val: '%s', entry )) + ')', data)) + ")"   # in ((%s,%s), (%s, %s), ...)
						flatdata = []
						for entry in data: 
							flatdata += list(entry)
						self.reload(objtype, SQL(whereclause, *flatdata))
					else:
						raise ValueError("Doesn't know how to reload object of type " + obj.__class__.__name__ + " with cache field : " + fieldname)

