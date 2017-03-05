from scrapy.exceptions import DropItem
import scrapyprj.alphabay_forum.items as items
from scrapyprj.database.orm import *
import scrapyprj.database as database
import scrapyprj.database.db as db
import peewee

class save2db(object):

	def process_item(self, item, spider):
		if not 'model' in item.keys():
			raise Exception("Sent an item with no 'model' key to " + self.__class__.__name__ + " pipeline")
	
		spider.dao.enqueue(item['model'])
		return item
		