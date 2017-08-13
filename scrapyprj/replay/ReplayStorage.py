from scrapy.http import Request, Response, TextResponse, HtmlResponse
import time
import json
import os
import io
from IPython import embed
from scrapy.utils.reqser import request_to_dict, request_from_dict
import collections
import logging
import traceback
import base64
from scrapy.utils.request import request_fingerprint
import re

# This class save/load scrapy Responses.
# There is not native tools to serialize responses, so we do quite a lot of manual work.
# Unit tests are available for this class : python -m unittest test_fixtures.TestReplayStorage
class ReplayStorage(object):
	class ResponseInfo:
		def __init__(self):
			fingerprint = None
			filename = None

	def __init__(self, spider, storage_dir):
		self.storage_dir = storage_dir
		self.spider = spider
		self.actual_index = None
		self.actual_index_offset = 0
		self.logger = logging.getLogger('ReplayStorage')

	def make_dir(self):
		if not os.path.exists(self.get_dir()):
			os.makedirs(self.get_dir())

	def delete_dir(self):
		final_dir = self.get_dir()
		if os.path.exists(final_dir):
			for root, dirs, files in os.walk(final_dir, topdown=False):
				for name in files:
					os.remove(os.path.join(root, name))
				for name in dirs:
					os.rmdir(os.path.join(root, name))
			os.rmdir(final_dir)

	def save(self, response):
		filename = self.make_filename(self.make_unique_name(response))
		with open(filename, 'wb') as f:	
			f.write(bytes(self.encode_response(response)))
		return filename

	def load(self, filename):
		try:
			with open(filename, 'r') as f:
				response =  self.decode_response(f.read())
			return response
		except Exception as e:
			self.logger.error('Cannot reload response %s. Error : %s\n%s' % (filename, e, traceback.format_exc()))
			raise

	def make_filename(self, filename):
		return os.path.join(self.storage_dir, self.spider.name, filename)

	def get_dir(self):
		return os.path.join(self.storage_dir,self.spider.name)

	def make_unique_name(self, response):
		index = str(int(round(time.time() * 1000, 0)))
		if self.actual_index is not None:
			if self.actual_index == index:
				self.actual_index_offset+=1
			else:
				self.actual_index = None
				self.actual_index_offset = 0
		else:
			self.actual_index = index
			self.actual_index_offset = 0

		return "%s_%04d_%s" %  (index,  self.actual_index_offset, request_fingerprint(response.request))

	def encode_response(self, response):
		return json.dumps(self.recurse_to_dict(response))

	def decode_response(self, j):
		temp = json.loads(j)
		return self.recurse_from_dict(temp)

	def response_to_dict(self, response):
		data = {}
		data['body'] = base64.b64encode(response.body)
		data['status'] = response.status
		data['url'] = response.url
		data['flags'] = response.flags
		data['headers'] = response.headers
		if hasattr(response, 'meta'):
			data['meta'] = response.meta
		data['request'] = response.request
		return data

	def response_from_dict(self, data,cls=HtmlResponse):
		body = base64.b64decode(data['body'])
		for k in data:
			if isinstance(data[k], unicode):
				data[k] = data[k].encode('utf8')
		return cls(body=body, headers=data['headers'], status=data['status'], url=data['url'], flags=data['flags'], request=self.recurse_from_dict(data['request']))

	def recurse_to_dict(self, node=None):
		newnode = None
		if isinstance(node, dict):
			newnode = {}
			for k in node:
				newnode[k] = self.recurse_to_dict(node[k])
		elif isinstance(node, tuple):
			newnode = tuple(map(self.recurse_to_dict, node))
		elif isinstance(node, list):
			newnode = map(self.recurse_to_dict, node)
		elif isinstance(node, Request):
			newnode = self.recurse_to_dict(request_to_dict(node))
			newnode['__request__'] = node.__class__.__name__
		elif isinstance(node, Response):
			newnode = self.recurse_to_dict(self.response_to_dict(node))
			newnode['__response__'] = node.__class__.__name__
		else:
			if isinstance(node, unicode):
				node = node.encode('utf8')
			newnode = node
		return newnode

	def recurse_from_dict(self, node):
		newnode = None
		if isinstance(node, dict):
			if '__response__' in node:
				if node['__response__'] == 'Response':
					cls = Response
				elif node['__response__'] == 'TextResponse':
					cls = TextResponse
				else:
					cls = HtmlResponse

				newnode = self.response_from_dict(node, cls)
		
			elif '__request__' in node:
				newnode = request_from_dict(node)
				for k in newnode.meta:
					newnode.meta[k] = self.recurse_from_dict(newnode.meta[k])
			else:
				for k in node:
					newnode[k] = self.recurse_from_dict(node[k])
		elif isinstance(node, tuple):
			newnode = tuple(map(self.recurse_from_dict, node))
		elif isinstance(node, list):
			newnode = map(self.recurse_from_dict, node)
		else:
			if isinstance(node, unicode):
				node = node.encode('utf8')
			newnode = node

		return newnode

	def saved_response_filenames(self):
		storagedir = self.get_dir()
		files = []
		for file in os.listdir(storagedir):
			files.append(os.path.join(storagedir, file))

		files.sort()
		
		for file in files:
			yield file

	def saved_response_info(self):
		i = 0
		for filename in self.saved_response_filenames():
			fileinfo = self.ResponseInfo()
			fileinfo.filename = filename
			fileinfo.position = i
			i+=1
			m = re.search(r'\d+_\d+_([0-9a-fA-F]+)', filename)
			if m:
				fileinfo.fingerprint = m.group(1)
			else:
				raise Exception('Cannot find fingerprint from filename')
			yield fileinfo

	def saved_response(self):
		for filename in self.saved_response_filenames():
			yield self.load(filename)
