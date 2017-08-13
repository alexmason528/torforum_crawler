from scrapy import signals, Item, Request
import logging
import os
from IPython import embed
from scrapy.utils.request import request_fingerprint
from scrapyprj.replay.ReplayStorage import ReplayStorage
from scrapyprj.replay.ReplayRequest import ReplayRequest
import traceback

class ReplaySpiderMiddleware(object):
	SPIDER_ATTRIBUTE = '__replay_middleware__'
	STORAGE_FOLDER = 'replayfolder'
	def __init__(self, settings):
		if 'MODE' in settings:
			self.replay = True if settings['MODE'] == 'replay' else False
		else:
			self.replay = False

		self.logger = logging.getLogger('ReplaySpiderMiddleware')
		self.storage = None
		self.folder_deleted = {}
		self.item_buffer = []
		self.filenames_by_fingerprint = {}
		self.remaining_filenames = {}

	@classmethod
	def from_crawler(cls, crawler):
		o = cls(crawler.settings)
		crawler.signals.connect(o.spider_opened, signal=signals.spider_opened)
		crawler.signals.connect(o.spider_closed, signal=signals.spider_closed)
		return o

	def spider_opened(self, spider):
		self.storage = ReplayStorage(spider, self.STORAGE_FOLDER)
		if not self.replay and spider.name not in self.folder_deleted:
			self.folder_deleted[spider.name]  = True
			self.storage.delete_dir()
			self.storage.make_dir()

		if self.replay:
			setattr(spider, self.SPIDER_ATTRIBUTE, self)	# We need to do some work in spider IDLE callback. 

	def spider_closed(self, spider):
		pass

	def process_spider_input(self, response, spider):
		if not self.replay:
			self.save(response)

	def process_spider_output(self, response, result, spider):
		for x in result:
			if self.replay:
				if isinstance(x, Item): # Don't yield requests in replay mode
					yield x
				elif isinstance(x, Request):
					requests_generator = self.yield_responses_from_spider_request(x) 	# This returns a ReplayRequest which already contain the response.
					if requests_generator is not None:
						for request in requests_generator:
							yield request
				else:
					yield x
			else:
				yield x

	def process_start_requests(self, start_requests, spider):
		if self.replay:
			for responseinfo in self.storage.saved_response_info():
				if responseinfo.fingerprint not in self.filenames_by_fingerprint:
					self.filenames_by_fingerprint[responseinfo.fingerprint] = []

				self.filenames_by_fingerprint[responseinfo.fingerprint].append(responseinfo.filename)
				self.remaining_filenames[responseinfo.filename] = True

			for x in start_requests:
				requests_generator = self.yield_responses_from_spider_request(x)	# This returns a ReplayRequest which already contain the response.
				if requests_generator is not None:
					for request in requests_generator:
						yield request
		else:
			for x in start_requests:
				yield x

	def yield_responses_from_spider_request(self, request):
		fingerprint = request_fingerprint(request)
		if fingerprint in self.filenames_by_fingerprint:
			for filename in self.filenames_by_fingerprint[fingerprint]:
				if filename in self.remaining_filenames:
					del self.remaining_filenames[filename]
					yield self.make_request_from_response(self.storage.load(filename))

	def get_remaining_response_requests(self):
		for filename in self.remaining_filenames:
			yield self.make_request_from_response(self.storage.load(filename))

	def process_spider_exception(self, response, exception, spider):
		self.logger.error("%s \n %s" % (exception, traceback.format_exc()))

	def make_request_from_response(self, response):
		request = response.request.copy()
		request.meta['shared'] = False
		request._meta['__replay__response__'] = response
		return request

	def save(self, response):
		try:
			self.storage.save(response)
		except Exception as e:
			self.logger.error("%s \n %s" % (e, traceback.format_exc()))
