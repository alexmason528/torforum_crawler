from scrapy.exceptions import DropItem
import torforum_crawler.alphabayforum.items as items
from torforum_crawler.database.orm import *
import torforum_crawler.database as database
import torforum_crawler.database.db as db

class SaveToDBPipeline(object):
	threadlist = {}
	thread_queue = list();

	def open_spider(self, spider):
		try:
			self.forum = models.Forum.get(spider=spider.name)
		except:
			raise Exception("No forum entry exist in the database for spider " + spider.name)

		spider.pipeline = self
		self.usermap = {}
		for user in models.User.select().where(models.User.forum == self.forum):
			self.usermap[user.username] = user;

	def process_item(self, item, spider):

		if type(item) == items.Thread:
			dbthread = models.Thread()
			
			dbthread.forum 		= self.forum
			dbthread.title 		= item['title']
			dbthread.relativeurl = item['relativeurl']
			dbthread.fullurl 	= item['fullurl']
			dbthread.external_id= item['threadid']
			dbthread.last_update= item['last_update']

			if item['author_username'] not in self.usermap:
				self.usermap[item['author_username']] = models.User.create_or_get(username=item['author_username'], forum=self.forum)[0]
			dbthread.author 	= self.usermap[item['author_username']]
			

			self.thread_queue.append(dbthread)	# Will be flushed by the spider to do bulk insertion
			pass

	def flush_threads(self):
		if len(self.thread_queue) > 0 :
			with database.db.proxy.atomic():
				data = list(map(lambda x: (x._data) , self.thread_queue))
				chunksize = 100
				for idx in range(0, len(data), chunksize):
					q = models.Thread.insert_many(data[idx:idx+chunksize]).sql()
					db.proxy.execute_sql(self.add_onduplicate_key(q[0], models.Thread.updatable_fields), q[1])
				

		self.thread_queue = []

	#Monkey patch to handle peewee<s limitation for On duplicate update close.
	def add_onduplicate_key(self, sql, fields):
		return sql + " on duplicate key update " + ','.join(map(lambda x: x.db_column+"=values("+x.db_column+")", fields))