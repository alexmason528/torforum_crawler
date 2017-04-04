from scrapyprj.spiders.MarketSpider import MarketSpider
from scrapy.shell import inspect_response
from scrapy.http import FormRequest,Request
import scrapy
import re
from IPython import embed
import parser
import scrapyprj.spider_folder.dreammarket.items as items
from urlparse import urlparse, parse_qsl
import json


class DreamMarketSpider(MarketSpider):
	name = "dreammarket"

	def __init__(self, *args, **kwargs):
		super(DreamMarketSpider, self).__init__( *args, **kwargs)
		self.logintrial = 0
		self.handling_ddos = False

		self.max_concurrent_requests = 1	# Scrapy config
		self.download_delay = 4				# Scrapy config

		self.request_queue_chunk = 1 		# Custom Queue system


		self.parse_handlers = {
				'index' : self.parse_index,
				'ads_list' : self.parse_ads_list,
				'ads' : self.parse_ads,
				'user' : self.parse_user
			}

	def start_requests(self):
		yield self.make_request('index')

	def make_request(self, reqtype,  **kwargs):

		if 'url' in kwargs:
			kwargs['url'] = self.make_url(kwargs['url'])

		if reqtype == 'index':
			req = Request(self.make_url('index'))
			if 'donotparse' in kwargs:
				req.meta['donotparse'] = True
			req.dont_filter=True
		elif reqtype == 'captcha_img':
			req  = Request(kwargs['url'])
			req.dont_filter = True

		elif reqtype == 'dologin':
			req = self.create_request_from_login_page(kwargs['response'])
			req.meta['req_once_logged'] = kwargs['req_once_logged']
			req.dont_filter=True
		elif reqtype == 'ddos_protection':
			req = self.create_request_from_ddos_protection(kwargs['response'])
			req.meta['req_once_logged'] = kwargs['req_once_logged']
			self.handling_ddos = True
			req.meta['ddos_protection'] = True
			req.dont_filter=True
		elif reqtype in ['ads_list', 'ads', 'user']:
			req = Request(self.make_url(kwargs['url']))


		req.meta['reqtype'] = reqtype   # We tell the type so that we can redo it if login is required
		req.meta['proxy'] = self.proxy  #meta[proxy] is handled by scrapy.
		req.meta['download_slot'] = self.proxy	# Concurrent request per domain are counted by slot. We explicitly give a slot for the proxy.

		if 'priority' in kwargs:
			req.priority = kwargs['priority']

		return req


	def parse(self, response):
		if not self.loggedin(response):	
			if self.isloginpage(response):
				self.logger.debug('Faced a login page.')
				if self.logintrial > self.settings['MAX_LOGIN_RETRY']:
					raise Exception("Too many failed login trials. Giving up.")
				self.logger.info("Trying to login.")
				self.logintrial += 1

				self.enqueue_request( self.make_request('dologin', req_once_logged=response.request, response=response) )

			elif self.is_ddos_protection_form(response):
				self.logger.debug('Faced a DDOS Protection page.')
				raise RuntimeError('DDOS Protection. Slow down the Crawler')

			elif self.is_logged_elsewhere(response) or self.is_session_expired(response):
				self.logger.debug('Need to relog')
				self.enqueue_request( self.make_request('index', priority=2, donotparse=True) )

				response.request.dont_filter = True
				self.enqueue_request( response.request )
			else:
				inspect_response(response, self)
				raise Exception("Not implemented yet, figure what to do here !")
		else : 
			self.logintrial = 0

			# We restore the missed request when protection kicked in
			if response.meta['reqtype'] == 'dologin':
				self.enqueue_request( response.meta['req_once_logged'] )

			elif response.meta['reqtype'] == 'ddos_protection':
				self.handling_ddos = False
				self.enqueue_request( response.meta['req_once_logged'] )
			
			# Normal parsing
			else:
				for x in self.parse_handlers[response.meta['reqtype']].__call__(response):
					if isinstance(x, scrapy.Request):
						self.enqueue_request(x)
					else:
						yield x

		
	def parse_index(self, response):
		if 'donotparse' in response.meta and response.meta['donotparse']:
			self.logger.debug('Do not parse index')
		else:
			depth0_categories = response.css('.main .sidebar .category a::attr(href)').extract()
			for link in depth0_categories:
				yield self.make_request('ads_list', url=link)

	def parse_ads_list(self, response):

		ads_url = response.css(".main .content .shopItem .oTitle>a::attr(href)").extract()
		for url in ads_url:
			yield self.make_request('ads', url=url)

		next_page_url = response.css(".main .content .pageNavContainer ul.pageNav li a.lastPager::attr(href)").extract_first()
		if next_page_url: 
			yield self.make_request('ads_list', url=next_page_url)

	def parse_ads(self, response):
		item = items.Ads()

		item['title'] = response.css('.viewProduct .title::text').extract_first().strip()
		details = response.css('div.tabularDetails>div')
		for div in details:
			label = div.css('label:first-child')
			label_txt = self.get_text(label).lower()
			span = div.xpath('./span')

			if label_txt == 'vendor':
				link = span.css('a:first-child')
				item['vendor_username'] = link.css('::text').extract_first().strip()
				url = link.css('::attr(href)').extract_first().strip()
				yield self.make_request('user', url = url)
			elif label_txt == 'price':
				item['price'] = self.get_text(span)
			elif label_txt == 'ships to':
				item['ships_to'] = self.get_text(span)
			elif label_txt == 'ships from':
				item['ships_from'] = self.get_text(span)
			elif label_txt == 'escrow':
				item['escrow'] = self.get_text(span)
			else:
				self.logger.warning('Found an ads detail (%s) that is unknown to this spider. Consider hadnling it.' % label_txt)

		item['description'] = self.get_text(response.css("#offerDescription"))

		item['offer_id'] = dict(parse_qsl(urlparse(response.url).query))['offer']
		
		try:
			item['category'] = self.get_active_category(response)
		except Exception, e:
			self.logger.warning('Cannot determine ads category : %s' % e)

		try:
			item['shipping_options'] = json.dumps(self.get_shipping_options(response))
		except Exception, e:
			self.logger.warning('Cannot determine shipping options : %s' % e)

		item['full_url'] = response.url

		yield item
	
	def parse_user(self, response):
		pass


	def loggedin(self, response):
		profile_links = response.css('.main .headNavitems ul li a[href="./profile"]')
		if profile_links and len(profile_links) > 0:
			return True

		return False
		

	def isloginpage(self, response):
		title = response.css('head title::text').extract_first()
		if title:
			if 'login' in title.lower():
				return True
		
		return False

	def is_ddos_protection_form(self, response):
		ddos_form = response.css('form div.ddos').extract()
		return True if len(ddos_form) > 0 else False

	def is_logged_elsewhere(self, response):
		return True if 'You have been logged in elsewhere' in response.body else False

	def is_session_expired(self, response):
		return True if 'Your session has expired' in response.body else False

	def create_request_from_ddos_protection(self, response):
		challenge = ''.join(response.css('.iline').xpath('./label[contains(text(), "Challenge")]/../text()').extract()).strip()
		captcha_src = response.css('label[for="captcha"] img::attr(src)').extract_first().strip()
		
		code = parser.expr(challenge).compile()	# Code injection safe eval.
	 	result = eval(code)
		self.logger.info('Answering DDOS protection challenge "%s" with answer %s' % (challenge, result))

		req = FormRequest.from_response(response, formdata={'result' : str(result)}, priority=5)
		req.meta['captcha'] = {		# CaptchaMiddleware will take care of that.
			'request' : self.make_request('captcha_img', url=captcha_src),
			'name' : 'captcha',
			'preprocess' : 'DreamMarketRectangleCropper'	# Preprocess image to extract what's within the rectangle
			}
		return req




	def create_request_from_login_page(self, response):
		username_txtbox_list = response.css('.formInputs').xpath('.//label[contains(text(), "Username")]/..').css('input[value=""], input[value="%s"]' % self.login['username'])
		password_txtbox_list = response.css('.formInputs').xpath('.//label[contains(text(), "Password")]/..').css('input[value=""]')
		captcha_txt_id = response.css('.formInputs').xpath('.//label[contains(text(), "Captcha code")]').css('::attr(for)').extract_first()

		#The website try to mislead us by adding a bunch of random hidden textbox next to username and password.
		# We aprse css with regex to find which one are hidden.
		
		# Username
		style = ''.join(response.css('style').extract())

		username_txtbox_list2 = []
		for txtbox in username_txtbox_list:
			nodeid = txtbox.xpath("@id").extract_first()
			regex = '#%s\s*\{[^\}]*display\s*:\s*none\s*;[^\}]*\}' % nodeid
			m = re.search(regex, style)
			if not m:
				username_txtbox_list2.append(txtbox)

		#Password
		password_txtbox_list2 = []
		for txtbox in password_txtbox_list:
			nodeid = txtbox.xpath("@id").extract_first()
			regex = '#%s\s*\{[^\}]*display\s*:\s*none\s*;[^\}]*\}' % nodeid
			m = re.search(regex, style)
			if not m:
				password_txtbox_list2.append(txtbox)

		#Success validation
		if len(username_txtbox_list2) != 1:
			inspect_response(response, self)
			raise Exception("Cannot find the right username textbox. There is %d candidates" % len(username_txtbox_list))

		username_txt_id = username_txtbox_list2[0].xpath("@id").extract_first()
		
		if len(password_txtbox_list2) != 1:
			raise Exception("Cannot find the right username textbox. There is %d candidates" % len(username_txtbox_list))
		password_txt_id = password_txtbox_list2[0].xpath("@id").extract_first()

		if not captcha_txt_id:
			raise Exception("Cannot find captcha text box in login page")

		# We have the ID of the textbox, let's find their form name
		username_formname = response.css('#%s::attr(name)' % username_txt_id).extract_first()
		password_formname = response.css('#%s::attr(name)' % password_txt_id).extract_first()
		captcha_formname = response.css('#%s::attr(name)' % captcha_txt_id).extract_first()

		if not username_formname:
			raise Exception("Cannot find username text box name in login page")
		
		if not password_formname:
			raise Exception("Cannot find password text box name in login page")
		
		if not captcha_formname:
			raise Exception("Cannot find captcha text boxname  in login page")

		captcha_src = response.css('.captcha img::attr(src)').extract_first()	# The captcha url

		data  = {}
		data[username_formname] =  self.login['username']
		data[password_formname] =  self.login['password']
		captcha_src = response.css('.captcha img::attr(src)').extract_first()
		if not captcha_src:
			raise Exception('Cannot find Captcha src')

		req = FormRequest.from_response(response, formdata=data)
		req.meta['captcha'] = {		# CaptchaMiddleware will take care of that.
			'request' : self.make_request('captcha_img', url=captcha_src),
			'name' : captcha_formname,
			'preprocess' : 'DreamMarketRectangleCropper'	# Preprocess image to extract what's within the rectangle
			}

		return req


	def get_active_category(self, response):
		categories = response.css('.sidebar.browse>div.category')
		category_list = []

		actual_depth = 0
		last_depth = -1
		for div in categories:
			name = ''.join(div.xpath('./a/text()').extract()).strip()
			category_list.append(name)

			if len(div.css('.selected')) > 0:
				break

			nodeclass = div.xpath('@class').extract_first();
			m = re.search('depth(\d+)', nodeclass)
			if m :
				actual_depth = int(m.groups(1)[0])
			else:
				raise RuntimeError("Depth not specified in category menu")

			if (actual_depth <= last_depth):
				category_list = category_list[:-1]

			last_depth = actual_depth

		return '/'.join(category_list)

	def get_shipping_options(self, response):
		options_list = []
		options = response.css('.shippingTable tr')
		for option in options:
			option_dict = {
				'price' : self.get_text(option.css('td:first-child')),
				'name' : self.get_text(option.css('td:nth-child(2)'))
				}
			options_list.append(option_dict)
		return options_list


