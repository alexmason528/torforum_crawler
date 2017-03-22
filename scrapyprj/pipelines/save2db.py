import scrapyprj.spider_folder.alphabay_forum.items as items

class save2db(object):

	def process_item(self, item, spider):
		if not 'model' in item.keys():
			raise Exception("Sent an item with no 'model' key to %s pipeline" % self.__class__.__name__)
	
		spider.dao.enqueue(item['model'])
		return item
		