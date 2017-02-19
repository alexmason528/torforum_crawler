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

		dbthread.forum 		= spider.dao.forum
		dbthread.title 		= item['title']
		dbthread.external_id= item['threadid']

		if 'relativeurl' in item:
			dbthread.relativeurl = item['relativeurl']
		
		if 'fullurl' in item:
			dbthread.fullurl 	= item['fullurl']
		
		if 'last_update' in item:	
			dbthread.last_update= item['last_update']

		dbthread.author = spider.dao.get_or_create(models.User, forum=spider.dao.forum, username= item['author_username'])
		if not dbthread.author:
			raise DropItem("Invalid Thread : Unable to get User from database. Cannot respect foreign key constraint.")
		elif not dbthread.author.id :
			raise DropItem("Invalid Thread : User foreign key was read from cache but no record Id was available. Cannot respect foreign key constraint")

		return dbthread


	def map_message(self, item, spider):
		if type(item) != items.Message:
			raise Exception("Expecting an item of type items.Message. Got : " + type(item).__name__ )

		dbmsg = models.Message()

		self.drop_if_empty(item, 'author_username')
		self.drop_if_missign(item, 'contenttext')
		self.drop_if_empty(item, 'contenthtml')
		self.drop_if_empty(item, 'threadid')

		dbmsg.thread = spider.dao.get(models.Thread, forum =spider.dao.forum, external_id = item['threadid'])	#Thread should exist in database
		if not dbmsg.thread:
			raise DropItem("Invalid Message : Unable to get Thread from database. Cannot respect foreign key constraint.")
		elif not dbmsg.thread.id :
			raise DropItem("Invalid Message : Thread foreign key was read from cache but no record Id was available. Cannot respect foreign key constraint")

		dbmsg.forum = dbmsg.thread.forum
		dbmsg.author = spider.dao.get_or_create(models.User, forum=spider.dao.forum, username= item['author_username'])

		if not dbmsg.author:
			raise DropItem("Invalid Message : Unable to get User from database. Cannot respect foreign key constraint.")
		elif not dbmsg.author.id :
			raise DropItem("Invalid Message : Author foreign key was read from cache but no record Id was available. Cannot respect foreign key constraint")

		dbmsg.external_id = item['postid']	
		dbmsg.contenttext= item['contenttext']
		dbmsg.contenthtml= item['contenthtml']

		if 'posted_on' in item:
			dbmsg.posted_on = item['posted_on']
		
		return dbmsg

	def drop_if_missign(self, item, field):
		if field not in item:
			raise DropItem("Missing %s in %s" % (field, item))

	def drop_if_empty(self, item, field):
		self.drop_if_missign(item, field)
		
		if not item[field]:
			raise DropItem("Empty %s in %s" % (field, item))
