from torforum_crawler.database.orm.models import *
import torforum_crawler.database as database
import inspect
from peewee import *
from scrapy.conf import settings

class Cache:

	cachekey = {
		'Thread' : 'external_id',
		'User' : 'username',
		'CaptchaQuestion' : 'hash',
		'Message' : 'external_id'
	}

	def __init__(self):
		self.cachedata = {}

	def unsafewrite(self, obj):
		keyname = self.getkey(obj.__class__)
		keyval = obj._data[keyname]
		self.cachedata[obj.__class__.__name__][keyval] = obj

	def unsaferead(self, modeltype, keyval):
		if keyval in self.cachedata[modeltype.__name__]:
			if keyval in self.cachedata[modeltype.__name__]:
				return self.cachedata[modeltype.__name__][keyval]

		return None

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

	def getkey(self, modeltype):
		self.assertismodelclass(modeltype)
		if modeltype.__name__ in self.cachekey:
			return self.cachekey[modeltype.__name__]
		else:
			pk = modeltype._meta.primary_key.name
			self.cachekey[modeltype.__name__] = pk
			return pk

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
		keyval_list = []
		chunksize = 100
		if len(objlist) > 0 :
			modeltype = objlist[0].__class__
			keyname = self.getkey(modeltype)
			for obj in objlist:
				self.assertismodelclass(obj.__class__)			
				objtype = obj.__class__ if not objtype else objtype
				if obj.__class__ != objtype:
					raise ValueError("Trying to reload partial set of data of different type.")
				
				keyval_list.append(obj._data[keyname])

			for idx in range(0, len(keyval_list), chunksize):
				self.reload(modeltype, modeltype._meta.fields[keyname] << keyval_list[idx:idx+chunksize])

