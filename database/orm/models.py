import torforum_crawler.database.db as db
from peewee import *

#Extension to peewee model that allows to make models that 
# have some properties listed in another table respecting a predefined structure.
class BasePropertyOwnerModel(Model):
	keys = {}
	keyinitialized = False
	def __init__(self, *args, **kwargs):
		if not self.__class__._meta.keymodel:
			raise Exception("When using BasePropertyOwnerModel, Meta.keymodel must be defined")
		if not self.__class__._meta.valmodel:
			raise Exception("When using BasePropertyOwnerModel, Meta.valmodel must be defined")

		self._properties = {}
		self._valmodel_attributes = {}

		#Intercepts kwargs for _properties that goes in our property table.
		keytoremove = []
		keylist = self.__class__.get_keys()
		for k in kwargs:
			if k in keylist:
				if hasattr(self, k):
					raise KeyError("%s has a field named %s but it's also linked to a property table having a key of the same name." % (self.__class__.__name__, k))
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

	def setproperties_attribute(self, *args, **kwargs):
		for k in kwargs:
			self._valmodel_attributes[k] = kwargs[k]

	def getproperties(self):
		props = [];
		keylist = self.__class__.get_keys()
		for keyname in self._properties:
			if self._properties[keyname]:
				params = {}
				params['key'] =  keylist[keyname] 
				params['data'] =  self._properties[keyname]  
				params[self._meta.valmodel.owner.name] = self
				for attr in self._valmodel_attributes:	# Bring back the kwargs from the object creation and pass them to the property object if it has this attribute.
					params[attr] = self._valmodel_attributes[attr]
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


class Scrape(Model):
	id = PrimaryKeyField();
	start = DateTimeField()
	end = DateTimeField()
	reason = TextField()
	forum = ForeignKeyField(Forum, related_name='scrapes', db_column='forum')
	mode = CharField();


	class Meta:
		database = db.proxy 
		db_table = 'scrape'



class UserPropertyKey(Model):
	id = PrimaryKeyField()
	name = CharField()

	class Meta:
		database = db.proxy 
		db_table='user_propkey'

DeferredUser = DeferredRelation() #Overcome circular dependency
class UserProperty(BasePropertyModel):
	key = ForeignKeyField(UserPropertyKey, db_column='propkey')
	owner = ForeignKeyField(DeferredUser,  db_column='user')
	data = TextField()
	scrape = ForeignKeyField(Scrape, db_column='scrape')


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
	scrape = ForeignKeyField(Scrape, related_name='users', db_column='scrape')

	class Meta:
		database = db.proxy 
		db_table = 'user'
		indexes = (
 			(('forum', 'username'), True),	# unique index
			)

		#Custom properties, not part of peewee
		valmodel = UserProperty
		keymodel = UserPropertyKey

DeferredUser.set_model(User)	#Overcome circular dependency



class Thread(Model):
	id = PrimaryKeyField()
	external_id = CharField()
	forum = ForeignKeyField(Forum, related_name='threads', db_column='forum')
	title = TextField()
	author = ForeignKeyField(User, related_name='threads', db_column='author')
	relativeurl = TextField()
	fullurl = TextField()
	last_update = DateTimeField()
	scrape = ForeignKeyField(Scrape, related_name='threads', db_column='scrape')

	updatable_fields = [title, last_update, author, relativeurl, fullurl]

	class Meta:
		database = db.proxy 
		db_table = 'thread'
		indexes = (
 			(('forum', 'external_id'), True),	# unique index
			)



class MessagePropertyKey(Model):
	id = PrimaryKeyField()
	name = CharField()

	class Meta:
		database = db.proxy 
		db_table='message_propkey'

DeferredMessage = DeferredRelation() #Overcome circular dependency

class MessageProperty(BasePropertyModel):
	key = ForeignKeyField(UserPropertyKey, db_column='propkey')
	owner = ForeignKeyField(DeferredUser,  db_column='message')
	data = TextField()
	scrape = ForeignKeyField(Scrape, db_column='scrape')


	class Meta:
		primary_key = CompositeKey('owner', 'key')
		database = db.proxy 
		db_table='message_propval'

class Message(Model):
	id = PrimaryKeyField()
	forum = ForeignKeyField(Forum, related_name='messages', db_column='forum')
	external_id = CharField()
	thread = ForeignKeyField(Thread, related_name='messages', db_column='thread')
	author = ForeignKeyField(User, related_name='messages', db_column='author')
	contenttext = TextField()
	contenthtml = TextField()
	posted_on = DateTimeField()
	scrape = ForeignKeyField(Scrape, related_name='messages', db_column='scrape')

	class Meta:
		database = db.proxy 
		db_table = 'message'
		indexes = (
			(('forum', 'external_id'), True),	# unique index
		)
DeferredMessage.set_model(Message)	#Overcome circular dependency

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

class ScrapeStat(Model):
	id = PrimaryKeyField()
	scrape = ForeignKeyField(Scrape, related_name='stats', db_column='scrape')
	logtime = DateTimeField()
	request_sent = BigIntegerField()
	request_bytes = BigIntegerField()
	response_received = BigIntegerField()
	response_bytes = BigIntegerField()
	item_scraped = BigIntegerField()
	thread = BigIntegerField()
	message = BigIntegerField()
	user = BigIntegerField()
	message_propval = BigIntegerField()
	user_propval = BigIntegerField()

	class Meta : 
		database = db.proxy
		db_table = 'scrapestat'

