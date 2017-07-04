import collections

import scrapyprj.items.forum_items as forum_items
import scrapyprj.items.market_items as market_items
import logging
import re

class DataFormatterPipeline(object):

	def __init__(self, *args,**kwargs):
		self.filter_map = {
			market_items.User : {
				'public_pgp_key' : self.normlaize_pgp_key
			}
		}
		self.logger = logging.getLogger('DataFormatterPipeline')


	def process_item(self, item, spider):
		for item_type in self.filter_map:
			if isinstance(item, item_type):
				for key in self.filter_map[item_type]:
					if key in item:
						item[key] = self.filter_map[item_type][key].__call__(item['public_pgp_key'])
		
		return item



	def normlaize_pgp_key(self, key):
		begin = '-----BEGIN PGP PUBLIC KEY BLOCK-----'
		end = '-----END PGP PUBLIC KEY BLOCK-----'
		m = re.search('%s(.+)%s' % (begin, end), key,re.S)
		if m:
			newlines = []
			for line in m.group(1).splitlines():
				if re.search('version', line, re.IGNORECASE):
					continue
				newlines.append(line)
			content = ''.join(newlines)
			return '%s\n\n%s\n%s' % (begin, content, end)
		
		self.logger.warning('Failed to clean PGP key.')
		return key