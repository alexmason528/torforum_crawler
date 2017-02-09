import torforum_crawler.database.db as db
from peewee import *

class CaptchaQuestion(Model):
	id = BigIntegerField(primary_key = True)
	spider = CharField()
	hash = CharField(unique = True)
	question = TextField()
	answer = TextField()

	class Meta:
		database = db.proxy # We assign the proxy object and we'll switch it for a real connection in the configuration.
		db_table = 'captcha_questions'
		only_save_dirty = True