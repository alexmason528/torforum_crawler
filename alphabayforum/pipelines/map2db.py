from scrapy.exceptions import DropItem
import torforum_crawler.alphabayforum.items as items
from torforum_crawler.database.orm import *

class map2db(object):
	def process_item(self, item, spider):

		if type(item) == items.Thread:
			return {'model' : self.map_thread(item, spider)}	# Sends to SaveToDB
		if type(item) == items.Message:
			return {'model' : self.map_message(item, spider)}	# Sends to SaveToDB
		else:
			raise Exception('Unknown item type : ' + type(item))


	def map_thread(self, item, spider):
		if type(item) != items.Thread:
			raise Exception("Expecting an item of type items.Thread. Got : " + type(item).__name__ )

		dbthread = models.Thread()

		self.drop_if_empty(item, 'title')
		self.drop_if_empty(item, 'threadid')

		dbthread.forum 		= spider.marshall.forum
		dbthread.title 		= item['title']
		dbthread.external_id= item['threadid']

		if 'relativeurl' in item:
			dbthread.relativeurl = item['relativeurl']
		
		if 'fullurl' in item:
			dbthread.fullurl 	= item['fullurl']
		
		if 'last_update' in item:	
			dbthread.last_update= item['last_update']

		dbthread.author = spider.marshall.get_or_create(models.User, forum=spider.marshall.forum, username= item['author_username'])

		return dbthread


	def map_message(self, item, spider):
		if type(item) != items.Message:
			raise Exception("Expecting an item of type items.Message. Got : " + type(item).__name__ )

		dbmsg = models.Message()

		self.drop_if_empty(item, 'author_username')
		self.drop_if_empty(item, 'contenttext')
		self.drop_if_empty(item, 'contenthtml')
		self.drop_if_empty(item, 'threadid')

		dbmsg.thread = spider.marshall.get(models.Thread, forum =spider.marshall.forum, external_id = item['threadid'])	#Thread should exist in database
		dbmsg.forum = dbmsg.thread.forum
		dbmsg.author = spider.marshall.get_or_create(models.User, forum=spider.marshall.forum, username= item['author_username'])
		dbmsg.external_id = item['postid']
		if dbmsg.external_id == '142791':
			spider.logger.critical("Found it ")
		
		dbmsg.contenttext= item['contenttext']
		dbmsg.contenthtml= item['contenthtml']

		if 'posted_on' in item:
			dbmsg.posted_on = item['posted_on']
		
		return dbmsg



	def drop_if_empty(self, item, field):
		drop = False
		if field not in item:
			drop = True
		elif not item[field]:
			drop = True

		if drop:
			raise DropItem("Missing %s in %s" % (field, item))
