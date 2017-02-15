import torforum_crawler.database.db as db
from peewee import *




class Forum(Model):
	id = PrimaryKeyField()
	name = CharField()
	spider = CharField(unique=True)

	class Meta:
		database = db.proxy 
		db_table = 'forum'

class User(Model):
	id = PrimaryKeyField()
	forum = ForeignKeyField(Forum, related_name='users', db_column='forum')
	username = CharField()

	class Meta:
		database = db.proxy 
		db_table = 'user'


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
	external_id = CharField()
	thread = ForeignKeyField(Thread, related_name='messages', db_column='thread')
	author = ForeignKeyField(User, related_name='messages', db_column='author')
	sha256 = CharField()
	content = TextField()
	posted_on = DateTimeField()

	class Meta:
		database = db.proxy 
		db_table = 'message'



class CaptchaQuestion(Model):
	id = PrimaryKeyField()
	forum = ForeignKeyField(Forum, related_name='captcha_questions', db_column='forum')
	hash = CharField(unique = True)
	question = TextField()
	answer = TextField()

	class Meta:
		database = db.proxy # We assign the proxy object and we'll switch it for a real connection in the configuration.
		db_table = 'captcha_question'


