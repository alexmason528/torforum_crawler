from scrapy import Request
import logging
import collections
from IPython import embed
import re
from twisted.internet import reactor
from scrapy.utils.defer import defer_result
from scrapy.utils.spider import iterate_spider_output
from scrapyprj.spiders.ForumSpider import ForumSpider
from scrapyprj.spiders.MarketSpider import MarketSpider
import profiler

# This spiders will flush to database once all items are received.
# It will force the requets to be sent to the engine AFTER the items so that there is no race condition (like message dependent on threads).
class AutoflushMiddleWare(object):
	def __init__(self):
		self.logger = logging.getLogger('AutoflushMiddleWare')

	def process_spider_output(self, response, result, spider):
		if isinstance(spider, ForumSpider) or isinstance(spider, MarketSpider):
			requests = []
			profiler.start('autoflush_process')
			for x in result:
				if isinstance(x, Request):
					requests.append(x)
				else:
					yield x

			spider.dao.flush_all()	# Flush after yielding items

			for request in requests:
				yield request
			del requests

			profiler.stop('autoflush_process')
		else:
			for x in result:
				yield x

	





