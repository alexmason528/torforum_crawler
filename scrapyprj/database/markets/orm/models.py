import scrapyprj.database.db as db
import scrapyprj.database.orm as orm
from peewee import *


class Market(Model):
	id = PrimaryKeyField()
	name = CharField()
	spider = CharField(unique=True)

	class Meta:
		database = db.proxy 
		db_table = 'market'


class Process(Model):
	id = PrimaryKeyField();
	start = DateTimeField()
	end = DateTimeField()
	pid = IntegerField()
	cmdline = TextField()
	
	class Meta:
		database = db.proxy 
		db_table = 'process'


class Scrape(Model):
	id = PrimaryKeyField();
	process = ForeignKeyField(Process, 	related_name='scrapes', db_column='process')
	market = ForeignKeyField(Market, 	related_name='scrapes', db_column='market')
	start = DateTimeField()
	end = DateTimeField()
	reason = TextField()
	login = CharField()
	proxy = CharField()

	class Meta:
		database = db.proxy 
		db_table = 'scrape'


class ScrapeStat(Model):
	id = PrimaryKeyField()
	scrape = ForeignKeyField(Scrape, related_name='stats', db_column='scrape')
	logtime = DateTimeField()
	request_sent = BigIntegerField()
	request_bytes = BigIntegerField()
	response_received = BigIntegerField()
	response_bytes = BigIntegerField()
	item_scraped = BigIntegerField()
	ads = BigIntegerField()
	ads_propval = BigIntegerField()
	ads_feedback = BigIntegerField()
	ads_feedback_propval = BigIntegerField()
	user = BigIntegerField()
	user_propval = BigIntegerField()
	seller_feedback = BigIntegerField()
	seller_feedback_propval = BigIntegerField()


	class Meta : 
		database = db.proxy
		db_table = 'scrapestat'


class CaptchaQuestion(Model):
	id = PrimaryKeyField()
	market = ForeignKeyField(Market, related_name='captcha_questions', db_column='market')
	hash = CharField(unique = True)
	question = TextField()
	answer = TextField()

	class Meta:
		database = db.proxy # We assign the proxy object and we'll switch it for a real connection in the configuration.
		db_table = 'captcha_question'
		indexes = (
			(('market', 'hash'), True),	# unique index
		)		


################  User  ############### 

class UserPropertyKey(Model):
	id = PrimaryKeyField()
	name = CharField()

	class Meta:
		database = db.proxy 
		db_table='user_propkey'

DeferredUser = DeferredRelation() #Overcome circular dependency

class UserProperty(orm.BasePropertyModel):
	key = ForeignKeyField(UserPropertyKey, 	db_column='propkey')
	owner = ForeignKeyField(DeferredUser,  	db_column='user')
	data = TextField()
	scrape = ForeignKeyField(Scrape, 		db_column='scrape')


	class Meta:
		primary_key = CompositeKey('owner', 'key')
		database = db.proxy 
		db_table='user_propval'


class User(orm.BasePropertyOwnerModel):
	id = PrimaryKeyField()
	market = ForeignKeyField(Market, related_name='users', 	db_column='market')
	username = CharField()
	relativeurl = TextField()
	fullurl = TextField() 
	scrape = ForeignKeyField(Scrape, related_name='users', 	db_column='scrape')

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

#######################################


############### Ads ###################

class AdsPropertyKey(Model):
	id = PrimaryKeyField()
	name = CharField()

	class Meta:
		database = db.proxy 
		db_table='ads_propkey'

DeferredAds = DeferredRelation() #Overcome circular dependency

class AdsProperty(orm.BasePropertyModel):
	key 	= ForeignKeyField(AdsPropertyKey, 	db_column='propkey')
	owner 	= ForeignKeyField(DeferredAds,  	db_column='ads')
	data 	= TextField()
	scrape 	= ForeignKeyField(Scrape, 			db_column='scrape')


	class Meta:
		primary_key = CompositeKey('owner', 'key')
		database = db.proxy 
		db_table='ads_propval'


class Ads(Model):
	id 			= PrimaryKeyField()
	external_id = CharField()
	market 		= ForeignKeyField(Market, 	related_name='ads', db_column='market')
	title 		= TextField()
	seller 		= ForeignKeyField(User, 	related_name='ads', db_column='seller')
	relativeurl = TextField()
	fullurl 	= TextField()
	last_update = DateTimeField()
	scrape 		= ForeignKeyField(Scrape, 	related_name='ads', db_column='scrape')

	class Meta:
		database = db.proxy 
		db_table = 'ads'
		indexes = (
 			(('market', 'external_id'), True),	# unique index
			)

DeferredAds.set_model(Ads)	#Overcome circular dependency


###########################################



############### Ads Feedback ###################

class AdsFeedbackPropertyKey(Model):
	id = PrimaryKeyField()
	name = CharField()

	class Meta:
		database = db.proxy 
		db_table='ads_feedback_propkey'

DeferredAdsFeedback = DeferredRelation() #Overcome circular dependency

class AdsFeedbackProperty(orm.BasePropertyModel):
	key 	= ForeignKeyField(AdsFeedbackPropertyKey, 	db_column='propkey')
	owner 	= ForeignKeyField(DeferredAdsFeedback,  	db_column='feedback')
	data 	= TextField()
	scrape 	= ForeignKeyField(Scrape, 					db_column='scrape')

	class Meta:
		primary_key = CompositeKey('owner', 'key')
		database = db.proxy 
		db_table='ads_feedback_propval'


class AdsFeedback(Model):
	id = PrimaryKeyField()
	external_id = CharField()
	market 	= ForeignKeyField(Market, 	related_name='ads_feedback', 	db_column='market')
	ads 	= ForeignKeyField(Ads, 		related_name='feedback', 		db_column='ads')
	scrape 	= ForeignKeyField(Scrape, 	related_name='ads_feedback',	db_column='scrape')

	class Meta:
		database = db.proxy 
		db_table = 'ads_feedback'
		indexes = (
 			(('market', 'external_id'), True),	# unique index
			)

DeferredAdsFeedback.set_model(AdsFeedback)	#Overcome circular dependency


###########################################


############## User Feedback ###################

class SellerFeedbackPropertyKey(Model):
	id = PrimaryKeyField()
	name = CharField()

	class Meta:
		database = db.proxy 
		db_table='seller_feedback_propkey'

DeferredSellerFeedback = DeferredRelation() #Overcome circular dependency

class SellerFeedbackProperty(orm.BasePropertyModel):
	key 	= ForeignKeyField(SellerFeedbackPropertyKey, 	db_column='propkey')
	owner 	= ForeignKeyField(DeferredSellerFeedback,  	db_column='feedback')
	data 	= TextField()
	scrape 	= ForeignKeyField(Scrape, 					db_column='scrape')

	class Meta:
		primary_key = CompositeKey('owner', 'key')
		database = db.proxy 
		db_table='seller_feedback_propval'


class SellerFeedback(Model):
	id = PrimaryKeyField()
	external_id = CharField()
	market 	= ForeignKeyField(Market, 	related_name='seller_feedback',	db_column='market')
	seller 	= ForeignKeyField(User, 	related_name='feedback', 		db_column='seller')
	scrape 	= ForeignKeyField(Scrape, 	related_name='seller_feedback',	db_column='scrape')

	class Meta:
		database = db.proxy 
		db_table = 'seller_feedback'
		indexes = (
 			(('market', 'external_id'), True),	# unique index
			)

DeferredSellerFeedback.set_model(SellerFeedback)	#Overcome circular dependency


###########################################




