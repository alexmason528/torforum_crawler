from twisted.internet import defer
from twisted.internet.error import TimeoutError, DNSLookupError, \
        ConnectionRefusedError, ConnectionDone, ConnectError, \
        ConnectionLost, TCPTimedOutError
from twisted.web.client import ResponseFailed
from scrapy import signals
from scrapy.exceptions import IgnoreRequest
from scrapy.utils.misc import load_object
import logging
import os
from IPython import embed
from scrapy.utils.request import request_fingerprint

class ReplayRequestMiddleware(object):
	def __init__(self):
		self.logger = logging.getLogger('ReplayRequestMiddleware')

	def process_request(self, request, spider):
		if '__replay__response__' in request.meta:
			return request.meta['__replay__response__']	# Stop execution of request. Return response.