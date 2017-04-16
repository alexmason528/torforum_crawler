import scrapyprj.spider_folder.alphabay_forum.items as items
import collections

class save2db(object):

	def process_item(self, item, spider):
		if not 'model' in item.keys():
			raise Exception("Sent an item with no 'model' key to %s pipeline" % self.__class__.__name__)
		
		if isinstance(item['model'], collections.Iterable):
			for model in item['model']:
				spider.dao.enqueue(model, spider)
		else:		
			spider.dao.enqueue(item['model'], spider)
		
		return item['model']
		