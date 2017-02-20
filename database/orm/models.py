import torforum_crawler.database.db as db
from peewee import *


class BasePropertyOwnerModel(Model):
	keys = {}
	keyinitialized = False
	def __init__(self, *args, **kwargs):
		if not self.__class__._meta.keymodel:
			raise Exception("When using BasePropertyOwnerModel, Meta.keymodel must be defined")
		if not self.__class__._meta.valmodel:
			raise Exception("When using BasePropertyOwnerModel, Meta.valmodel must be defined")

		self._properties = {}
		#Intercepts kwargs for _properties that goes in our property table.
		keytoremove = []
		keylist = self.__class__.get_keys()
		for k in kwargs:
			if k in keylist:
				self._properties[k] = kwargs[k]
				keytoremove.append(k)
		for k in keytoremove:	# Remove entries from keywargs before passing the to the real peewee.Model
			del kwargs[k]


		super(BasePropertyOwnerModel, self).__init__(*args, **kwargs)

	# Intercepts _properties that goes in our external property table.
	def __setattr__(self, k ,v):
		keylist = self.__class__.get_keys()
		if k in keylist:
			self._properties[k] = v
		else:
			super(BasePropertyOwnerModel, self).__setattr__(k,v)

	def getproperties(self):
		props = [];
		keylist = self.__class__.get_keys()
		for keyname in self._properties:
			if self._properties[keyname]:
				params = {}
				params['key'] =  keylist[keyname] 
				params['data'] =  self._properties[keyname]  
				params[self._meta.valmodel.owner.name] = self
				props.append(self._meta.valmodel(**params))
		return props

	@classmethod
	def get_keys(cls):
		if not cls.keyinitialized:
			if not cls._meta.keymodel:
				raise Exception("When using BasePropertyOwnerModel, valmodel and keymodel must be defined")

			dbkeys = cls._meta.keymodel.select()
			for k in dbkeys:
				cls.keys[k.name] = k
			cls.keyinitialized = True
		return cls.keys

	class Meta:
		keymodel = None
		valmodel = None

class BasePropertyModel(Model):
	key = None
	data = None


#######################################################

class Forum(Model):
	id = PrimaryKeyField()
	name = CharField()
	spider = CharField(unique=True)

	class Meta:
		database = db.proxy 
		db_table = 'forum'





class UserPropertyKey(Model):
	id = PrimaryKeyField()
	name = CharField()

	class Meta:
		database = db.proxy 
		db_table='user_propkey'

DeferredUser = DeferredRelation()
class UserProperty(BasePropertyModel):
	key = ForeignKeyField(UserPropertyKey, db_column='propkey')
	owner = ForeignKeyField(DeferredUser,  db_column='user')
	data = TextField()

	class Meta:
		primary_key = CompositeKey('owner', 'key')
		database = db.proxy 
		db_table='user_propval'


class User(BasePropertyOwnerModel):
	id = PrimaryKeyField()
	forum = ForeignKeyField(Forum, related_name='users', db_column='forum')
	username = CharField()
	relativeurl = TextField()
	fullurl = TextField() 

	class Meta:
		database = db.proxy 
		db_table = 'user'
		indexes = (
 			(('forum', 'username'), True),	# unique index
			)

		#Custom properties, not part of peewee
		valmodel = UserProperty
		keymodel = UserPropertyKey

DeferredUser.set_model(User)





class Thread(Model):
	id = PrimaryKeyField()
	external_id = CharField()
	forum = ForeignKeyField(Forum, related_name='threads', db_column='forum')
	title = TextField()
	author = ForeignKeyField(User, related_name='threads', db_column='author')
	relativeurl = TextField()
	fullurl = TextField()
	last_update = DateTimeField()

	updatable_fields = [title, last_update, author, relativeurl, fullurl]

	class Meta:
		database = db.proxy 
		db_table = 'thread'
		indexes = (
 			(('forum', 'external_id'), True),	# unique index
			)


class Message(Model):
	id = PrimaryKeyField()
	forum = ForeignKeyField(Forum, related_name='messages', db_column='forum')
	external_id = CharField()
	thread = ForeignKeyField(Thread, related_name='messages', db_column='thread')
	author = ForeignKeyField(User, related_name='messages', db_column='author')
	contenttext = TextField()
	contenthtml = TextField()
	posted_on = DateTimeField()

	class Meta:
		database = db.proxy 
		db_table = 'message'
		indexes = (
			(('forum', 'external_id'), True),	# unique index
		)



class CaptchaQuestion(Model):
	id = PrimaryKeyField()
	forum = ForeignKeyField(Forum, related_name='captcha_questions', db_column='forum')
	hash = CharField(unique = True)
	question = TextField()
	answer = TextField()

	class Meta:
		database = db.proxy # We assign the proxy object and we'll switch it for a real connection in the configuration.
		db_table = 'captcha_question'
		indexes = (
			(('forum', 'hash'), True),	# unique index
		)		


