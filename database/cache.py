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

	def unsafewrite(self, obj, *fieldlist):
		fieldname, cacheid = self.getcacheid(obj)
		table = obj._meta.db_table
		if not cacheid:
			raise ValueError("Cannot write to cache object of type "  + obj.__class__.__name__ + " no usable id to identify the record.")
		if len(fieldlist) == 0 :
			self.cachedata[table][cacheid] = obj
		else:
			for field in fieldlist:	#Partial copy
				self.cachedata[table][cacheid]._data[field.name] = obj._data[field.name]	# Copy a single field from obj to the object stored in cache. (ob1.x = obj2.x)


	def unsaferead(self, modeltype, cacheid):
		table = modeltype._meta.db_table
		if table in self.cachedata:
			if cacheid in self.cachedata[table]:
				return self.cachedata[table][cacheid]

	def readobj(self, obj):
		fieldname, cacheid = self.getcacheid(obj)
		return self.read(obj.__class__, cacheid)


	# For a specific Model, returns the unique key used to cache the object.
	# return (fieldname, cacheid) 
	# fieldname is the name of the field used as a key. Can be a string for single key or a tuple for composite key
	# cacheid is the value used as the index in the cache. Can be anything (literal, string, tuple)

	def getcacheid(self, obj):
		objclass = obj.__class__
		self.assertismodelclass(objclass)
		if objclass._meta.db_table in self.cachekey:
			fieldname = self.cachekey[objclass._meta.db_table]
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

		raise ValueError("Trying to obtain the cache id from bbject " + obj.__class__.__name__ + " but no key data is usable. Cotnent : " + str(obj._data))
	
	# extract the value of the index from an object. index can be single field name or tuple of field name for composite key.
	def read_index_value(self, obj, idx):
		if isinstance(idx, tuple):	# we are dealing with a composite key
			complete = True
			keyval = tuple()
			for idx in idx :
				if idx in obj._data:
					keyval += (self.getfield_or_primarykey(obj._data[idx]),)	# Append to tuple
				else:
					complete  = False
					break
			return keyval if complete else None 
		elif isinstance(idx, str): 		# Single key
			if idx in obj._data:
				return self.getfield_or_primarykey(obj._data[idx])

	def getfield_or_primarykey(self, val):
		if issubclass(val.__class__, Model):		# It's a foreign key. Get the primary key
			val = val._data[val._meta.primary_key]
		return val


	def read(self, modeltype, keyval):
		self.assertismodelclass(modeltype)
		self.init_ifnotexist(modeltype)
		return self.unsaferead(modeltype, keyval)		

	def write(self, obj,*fieldlist):
		self.assertismodelclass(obj.__class__)
		self.init_ifnotexist(obj.__class__)
		self.unsafewrite(obj,*fieldlist)

	def bulkwrite(self, objlist, *fieldlist):
		for obj in objlist: 
			self.write(obj, *fieldlist)

	def init_ifnotexist(self, modeltype):
		if not modeltype._meta.db_table in self.cachedata:
			self.cachedata[modeltype._meta.db_table] = {}
	
	def reload(self, modeltype, whereclause, *fieldlist):
		self.assertismodelclass(modeltype)
		self.init_ifnotexist(modeltype)
		objects = modeltype.select().where(whereclause)
		for obj in objects:
			self.unsafewrite(obj, *fieldlist)

	def assertismodelclass(self, modeltype):
		if not inspect.isclass(modeltype):
			raise Exception("Type must be a Class")
		elif not issubclass(modeltype, Model):
			raise Exception("Given type must be a subclass of PeeWee.Model")

	def reloadmodels(self, objlist, *fieldlist):
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
						self.reload(modeltype, modeltype._meta.fields[fieldname] << data, *fieldlist)

					elif isinstance(fieldname, tuple): # composite key. Peewee doesn't support that easily, we have to do some manual work
						whereclause = '('+','.join(map(lambda x: "`%s`" % x, fieldname))+')'  # (`col1`, `col2`)
						whereclause += " in (" + ','.join(map(lambda entry: '('+','.join(map(lambda val: '%s', entry )) + ')', data)) + ")"   # in ((%s,%s), (%s, %s), ...)
						flatdata = []
						for entry in data: 
							flatdata += list(entry)
						self.reload(objtype, SQL(whereclause, *flatdata), *fieldlist)
					else:
						raise ValueError("Doesn't know how to reload object of type " + obj.__class__.__name__ + " with cache field : " + fieldname)

