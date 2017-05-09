from scrapy.exceptions import DropItem
import scrapyprj.spider_folder.alphabay_forum.items as items
from scrapyprj.database.forums.orm import *
from IPython import embed

class map2db(object):
	def process_item(self, item, spider):

		if type(item) == items.Thread:
			return {'model' : self.map_thread(item, spider)}	# Sends to SaveToDB
		elif type(item) == items.Message:
			return {'model' : self.map_message(item, spider)}	# Sends to SaveToDB
		elif type(item) == items.User:
			return {'model' : self.map_user(item, spider)}	# Sends to SaveToDB
		else:
			raise Exception('Unknown item type : ' + item.__class__.__name__)


	def map_thread(self, item, spider):
		if type(item) != items.Thread:
			raise Exception("Expecting an item of type items.Thread. Got : " + type(item).__name__ )

		dbthread = models.Thread()

		self.drop_if_empty(item, 'title')
		self.drop_if_empty(item, 'threadid')

		dbthread.forum 		= spider.forum
		dbthread.scrape 	= spider.scrape
		dbthread.title 		= item['title']
		dbthread.external_id= item['threadid']

		if 'relativeurl' in item:
			dbthread.relativeurl = item['relativeurl']
		
		if 'fullurl' in item:
			dbthread.fullurl 	= item['fullurl']
		
		if 'last_update' in item:	
			dbthread.last_update= item['last_update']

		dbthread.author = spider.dao.get_or_create(models.User,  username= item['author_username'], forum=spider.forum) # Unique key here
		dbthread.scrape = spider.scrape
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

		dbmsg.thread = spider.dao.get(models.Thread, forum =spider.forum, external_id = item['threadid'])	#Thread should exist in database
		if not dbmsg.thread:
			raise DropItem("Invalid Message : Unable to get Thread from database. Cannot respect foreign key constraint.")
		elif not dbmsg.thread.id :
			raise DropItem("Invalid Message : Thread foreign key was read from cache but no record Id was available. Cannot respect foreign key constraint")

		dbmsg.forum 	= dbmsg.thread.forum
		dbmsg.scrape 	= spider.scrape
		dbmsg.author 	= spider.dao.get_or_create(models.User, username= item['author_username'], forum=spider.forum) # Make sur only unique key in constructor
		dbmsg.scrape	= spider.scrape

		if not dbmsg.author:
			raise DropItem("Invalid Message : Unable to get User from database. Cannot respect foreign key constraint.")
		elif not dbmsg.author.id : # If this happens. Either data is not flush or bug.
			raise DropItem("Invalid Message : Author foreign key was read from cache but no record Id was available. Cannot respect foreign key constraint")

		dbmsg.external_id = item['postid']	
		dbmsg.contenttext = item['contenttext']
		dbmsg.contenthtml = item['contenthtml']

		if 'posted_on' in item:
			dbmsg.posted_on = item['posted_on']
		
		return dbmsg

	def map_user(self, item, spider):
		self.drop_if_empty(item, 'username')

		dbuser = models.User()	# Extended PeeWee object that handles properties in different table
		dbuser.username = item['username']
		
		dbuser.forum = spider.forum
		dbuser.scrape = spider.scrape
		dbuser.setproperties_attribute(scrape = spider.scrape)  #propagate the scrape id to the UserProperty model.

		#Proeprties with same name in model and item
		self.set_if_exist(item, dbuser, 'relativeurl')
		self.set_if_exist(item, dbuser, 'fullurl')
		self.set_if_exist(item, dbuser, 'joined_on')
		self.set_if_exist(item, dbuser, 'likes_received')
		self.set_if_exist(item, dbuser, 'last_activity')
		self.set_if_exist(item, dbuser, 'message_count')
		self.set_if_exist(item, dbuser, 'user_id')
		self.set_if_exist(item, dbuser, 'title')
		self.set_if_exist(item, dbuser, 'banner')

		return dbuser

	def set_if_exist(self, item, model, field):
		if field in item:
			model.__setattr__(field, item[field])

	def drop_if_missign(self, item, field):
		if field not in item:
			raise DropItem("Missing %s in %s" % (field, item))

	def drop_if_empty(self, item, field):
		self.drop_if_missign(item, field)
		
		if not item[field]:
			raise DropItem("Empty %s in %s" % (field, item))
