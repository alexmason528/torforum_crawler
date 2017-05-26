import scrapy
from datetime import datetime
from scrapyprj.database import db
from scrapyprj.ColorFormatterWrapper import ColorFormatterWrapper

from importlib import import_module
import os, time, sys, signal
import random
import logging
import pytz
from IPython import embed
from fake_useragent import UserAgent

from scrapy.downloadermiddlewares.cookies import CookiesMiddleware
from Cookie import SimpleCookie
from scrapy.mail import MailSender
from scrapy import Request
from urlparse import urlparse, parse_qsl

from twisted.internet import reactor

class BaseSpider(scrapy.Spider):
	user_agent  = UserAgent().random
	def __init__(self, *args, **kwargs):
		kwargs['settings'] = self.configure_image_store(kwargs['settings'])
		super(BaseSpider, self).__init__( *args, **kwargs)
		self.settings = kwargs['settings']	# If we don't do that, the setting sobject only exist after __init__()
		self.load_spider_settings()
		self.initlogs()
		self.configure_login()
		self.configure_proxy()
		self.mailer =  MailSender.from_settings(self.settings)
		
		if not hasattr(BaseSpider, '_allspiders'):
			BaseSpider._allspiders = {}

		if self.__class__ not in BaseSpider._allspiders:
			BaseSpider._allspiders[self.__class__] = []

		BaseSpider._allspiders[self.__class__].append(self)

		self.start_interrupt_polling()

		

		#Counters : We use this to distribute logins/proxies equally between spiders.
	def _initialize_counter(self, name, key=None, isglobal=False):
		if isglobal:
			cls = BaseSpider if len(self.__class__.__bases__) == 0 else self.__class__.__bases__[0]
		else:		
			cls = self.__class__

		if not hasattr(cls, '_counters'):
			cls._counters = {}

		if not name in cls._counters:
			cls._counters[name] = {}

		if key:
			if not key in cls._counters[name]:
				cls._counters[name][key] = 0

	def add_to_counter(self, name, key, val, isglobal=False):
		self._initialize_counter(name,key,isglobal)
		cnt = self.get_counter(name, isglobal=isglobal)
		cnt[key] += val
		cnt[key] = max(cnt[key], 0)
		self.logger.debug("Counter updated: %s = %s" % (name, cnt))

	def get_counter(self, name, key=None, isglobal=False):
		self._initialize_counter(name, isglobal=isglobal)
		if isglobal:
			cls = BaseSpider if len(self.__class__.__bases__) == 0 else self.__class__.__bases__[0]
		else:		
			cls = self.__class__

		if not key:
			return cls._counters[name]
		else:
			return cls._counters[name][key]

	#Return the requested login information from the spier settings.
	# attribute "login" must be given (-a login="paramValue" using the CLI)
	# attribute can be a numerical index or the login dict key. If not specified, a random entry is returned
	def configure_login(self, loginkey=None):
		if not hasattr(self.__class__, 'taken_logins'):
			self.__class__.taken_logins = {}	# Initialise that

		if not hasattr(self, 'login') or isinstance(self.login, basestring) or isinstance(self.login, list) or loginkey:
			if 'logins' not in self.spider_settings:
				raise Exception("No login defined in spider settings")

			if len(self.spider_settings['logins']) == 0:
				raise Exception("Empty login list in spider settings")			

			logininput = None;
			if loginkey:
				logininput = loginkey
			elif hasattr(self, 'login'):
				logininput = self.login
			elif 'login' in self.settings:
				logininput = self.settings['login']

			logindict = {}
			if isinstance(logininput, list):
				for k in logininput:
					if k in self.spider_settings['logins']:
						logindict[k] = self.spider_settings['logins'][k]
					else:
						raise ValueError("No login information with index %s" % k)
			else:
				logindict = self.spider_settings['logins'];

			if not logininput or isinstance(logininput, list):	#None or list
				key = self.pick_in_list(logindict.keys(), counter=self.get_counter('logins'))
				self.logger.debug("Using a random login information. Returning login for key : %s" % (key))
				
			elif isinstance(logininput, basestring):
				if logininput not in logindict:
					raise ValueError("No login information with index : %s" % logininput)
				key = logininput
			else:
				raise ValueError("logininput is of unsupported type %s" % str(type(logininput))) # Should never happend
			
			if loginkey and self._loginkey:
				self.add_to_counter('logins', self._loginkey, -1)
			
			self.login = logindict[key]
			self._loginkey = key
			self.logger.info('Using login %s' % self._loginkey)

			self.add_to_counter('logins', self._loginkey, 1)

		return self.login

	# Used for selection of proxy and login. We distribute usage equally, therefore the "counter" object
	def pick_in_list(self,items, counter=None):
		if len(items) == 0:
			raise ValueError("Cannot pick a value in an empty list")
		if not counter:
			n= random.randrange(0,len(items))
			return list(items)[n]

		for item in items:
			if item not in counter:
				counter[item] = 0

		count_min = None
		selected_key = None
		for k in counter:
			if counter[k]<count_min or count_min == None:
				count_min = counter[k]
				selected_key = k

		return selected_key			


	def resource(self, name):
		if name not in self.spider_settings['resources']:
			raise Exception('Cannot access resources %s. Ressource is not specified in spider settings.' % name)  
		return self.spider_settings['resources'][name]

	def make_url(self, url):
		endpoint = self.spider_settings['endpoint'].strip('/');
		prefix = self.spider_settings['prefix'].strip('/');
		if url.startswith('http'):
			return url
		elif url in self.spider_settings['resources'] :
			if prefix:
				return "%s/%s/%s" % (endpoint, prefix, self.resource(url).lstrip('/'))
			else:
				return "%s/%s" % (endpoint, self.resource(url).lstrip('/'))
		elif url.startswith('/'):
			return "%s/%s" % (endpoint, url.lstrip('/'))
		else:
			if prefix:
				return "%s/%s/%s" % (endpoint,prefix, url.lstrip('/'))
			else:
				return "%s/%s" % (endpoint, url.lstrip('/'))


	def initlogs(self):
		try:
			for logger_name in  self.settings['DISABLE_LOGGER'].split(','):
				logging.getLogger(logger_name).disabled=True
		except:
			pass

		try:
			colorformatter = ColorFormatterWrapper(self.logger.logger.parent.handlers[0].formatter)
			self.logger.logger.parent.handlers[0].setFormatter(colorformatter)
		except:
			pass


	def configure_proxy(self, proxykey=None):
		self._proxy_key = None

		if not hasattr(self, 'proxy') or proxykey:	# can be given by command line
			if not proxykey:
				if 'PROXY' in self.settings:  # proxy is the one to use. Proxies is the definition.
					if 'PROXIES' in self.settings and self.settings['PROXY'] in self.settings['PROXIES']:
						self._proxy_key = self.settings['PROXY']
					else:
						raise ValueError("Proxy %s does not exist in self.settings PROXIES " % self.settings['PROXY'])
				else:
					if 'PROXIES' in self.settings:
						if len(self.settings['PROXIES']) > 0:
							self._proxy_key = self.pick_in_list(self.settings['PROXIES'].keys(), counter=self.get_counter('proxies', isglobal=True))
			else:
				if 'PROXIES' not in self.settings or proxykey not in self.settings['PROXIES']:
					raise ValueError('Given Proxy name is not part of the list in setting file')

				if self._proxy_key:
					self.add_to_counter('proxies', self._proxy_key, -1, isglobal=True)
				self._proxy_key = proxykey

			if self._proxy_key:
				self.proxy = self.settings['PROXIES'][self._proxy_key]
				self.add_to_counter('proxies', self._proxy_key, 1, isglobal=True)
				self.logger.info('Using proxy %s' % self._proxy_key)

	def configure_image_store(self, settings):
		if 'IMAGE_STORE' in settings:
			actual_image_store = settings['IMAGE_STORE'].rstrip('/')
			settings.set('IMAGE_STORE', "%s/%s" % (actual_image_store, self.name) )
		return settings

	def set_timezone(self):
		if 'timezone' in self.spider_settings:
			self.timezone = pytz.timezone(self.spider_settings['timezone'])
			db.set_timezone(pytz.utc) 	# Sync db timezone with environment.
		else:
			raise ValueError('A timezone is required. Please set one in the spider settings.')

	# Load settings located in the spider folder.
	def load_spider_settings(self):
		self.spider_settings = {}
		setting_module = "%s.spider_folder.%s.settings" % (self.settings['BOT_NAME'], self.name)
		try:
			self.spider_settings = import_module(setting_module).settings
		except:
			self.logger.warning("Cannot load spider specific settings from : %s" % setting_module)			


	def to_utc(self, datetime):
		return datetime - self.timezone.localize(datetime).utcoffset()

	def localnow(self):
		return self.timezone.localize(datetime.now())

	def spider_closed(self, spider, reason):
		self.add_to_counter('logins', self._loginkey, -1)
		self.add_to_counter('proxies', self._proxy_key, -1, isglobal=True)

		self.logger.info("Spider resources released")

	def get_text(self, node):
		if node == None:
			return ""
			
		if isinstance(node, basestring):
			text=node.strip()
		else:
			text = ''.join(node.xpath(".//text()[normalize-space(.)]").extract()).strip()
		
		try:
			if isinstance(text, unicode):
				text = text.encode('utf-8', 'ignore')	# Encode in UTF-8 and remove unknown char.
			else:
				text = text.decode('utf-8', 'ignore').encode('utf-8', 'ignore')
		except:
			# Some hand crafted characters can throw an exception. Remove them silently.
			text = text.encode('cp1252', 'ignore').decode('utf-8','ignore') # Remove non-utf8 chars. 

		return text

	def get_text_first(self, nodes):
		if nodes == None:
			return ''	
		elif isinstance(nodes, basestring):
			return self.get_text(nodes)
		elif len(nodes) > 0:
			return self.get_text(nodes[0])
		else:
			return ""



	def set_cookies(self, cookie_string):
		cookie_middleware = self.get_cookie_middleware()

		if not cookie_middleware:
			self.logger.error("Trying to set cookies, but can't find cookie middleware.")
		else:
			jar = cookie_middleware.jars[None]
			cookies = SimpleCookie(cookie_string.encode('ascii'))
			cookie_dict = dict()
			for key in cookies:
				cookie_dict[key] = cookies.get(key).value

			req = Request(self.spider_settings['endpoint'], cookies=cookie_dict)
			cookie_middleware.jars[None].clear()
			cookie_middleware.process_request(req, self)	# Simulate a request with these cookies.

	def get_cookies(self):
		cookie_middleware = self.get_cookie_middleware()

		if not cookie_middleware:
			self.logger.error("Trying to set cookies, but can't find cookie middleware.")
		else:
			jar = cookie_middleware.jars[None]

		req = Request(self.spider_settings['endpoint'])
		jar.add_cookie_header(req)

		return  req.headers['Cookie'] if 'Cookie' in req.headers else ''

	def get_cookie_middleware(self):
		cookie_middleware = None
		for middleware in self.crawler.engine.downloader.middleware.middlewares:
			if isinstance(middleware, CookiesMiddleware):
				cookie_middleware = middleware
				break

		return cookie_middleware

	def downloader_still_active(self):
		for spider in BaseSpider._allspiders[self.__class__]:
			if len(spider.crawler.engine.slot.inprogress) > 0:
				return True

			if len(spider.crawler.engine.slot.scheduler) > 0:
				return True

		return False


	def send_mail(self,subject, body):
		if self.mailer and 'MAIL_RECIPIENT' in self.settings:
			to	= self.settings['MAIL_RECIPIENT']
			self.logger.info('Sending email to %s. Subject : %s' % (to, subject))
			self.mailer.send(to=to, subject=subject, body=body)
		else:
			self.logger.warning('Trying to send email, but smtp is not configured or no MAIL_RECIPIENT is defined in settings.')



	def start_interrupt_polling(self):
		if not hasattr(BaseSpider, '_interrupt_polling_started'):
			BaseSpider._interrupt_polling_started = True
			self.interrupt_polling_handler()	



	def interrupt_polling_handler(self):
		self.interrupt_polling_taskid = None
		self.poll_for_interrupt()
		self.interrupt_polling_taskid = reactor.callLater(5, self.interrupt_polling_handler)

	def poll_for_interrupt(self):
		self.logger.debug("Polling for interrupt file")
		if os.path.isfile('interrupt'):
			try:
				os.remove("interrupt")
			except:
				pass
			self.logger.info("Interrupt!")
			embed()
	
	def get_url_param(self, url, key):
         return dict(parse_qsl(urlparse(url).query))[key]		

  	def datetime_to_string(self, dt):
  		return dt.strftime("%Y-%M-%d %H:%M:%S")