from scrapy.exceptions import DropItem
import torforum_crawler.alphabayforum.items as items
from torforum_crawler.database.orm import *

class map2db(object):
	def process_item(self, item, spider):

		if type(item) == items.Thread:
			return {'model' : self.map_thread(item, spider)}	# Sends to SaveToDB
		else:
			raise Exception('Unknown item type : ' + type(item))


	def map_thread(self, item, spider):
		if type(item) != items.Thread:
			raise Exception("Expecting an item of type items.Thread. Got : " + type(item).__name__ )

		dbthread = models.Thread()
			
		dbthread.forum 		= spider.marshall.forum
		dbthread.title 		= item['title']
		dbthread.relativeurl = item['relativeurl']
		dbthread.fullurl 	= item['fullurl']
		dbthread.external_id= item['threadid']
		dbthread.last_update= item['last_update']

		dbthread.author = spider.marshall.get_or_create(models.User, forum=spider.marshall.forum, username= item['author_username'])

		return dbthread


