from scrapyprj.spiders.MarketSpider import MarketSpider
from scrapy.shell import inspect_response
from scrapy.http import FormRequest,Request
import scrapy
import re
from IPython import embed

class DreamMarketSpider(MarketSpider):
	name = "dreammarket"


	def __init__(self, *args, **kwargs):
		super(DreamMarketSpider, self).__init__( *args, **kwargs)
		self.logintrial = 0

		#print self.settings['DOWNLOADER_MIDDLEWARES'].__dict__

	def start_requests(self):
		yield self.make_request('index')

	def make_request(self, reqtype,  **kwargs):

		if 'url' in kwargs:
			kwargs['url'] = self.make_url(kwargs['url'])

		if reqtype == 'index':
			req = Request(self.make_url('index'))
			req.dont_filter=True
		elif reqtype == 'captcha_img':
			response = kwargs['response']
			captcha_src = response.css('.captcha img::attr(src)').extract_first()
			if not captcha_src:
				raise Exception('Cannot find Captcha src')
			req  = Request(self.make_url(captcha_src), callback=self.process_captcha)
			req.dont_filter = True

		elif reqtype == 'dologin':
			req = self.create_request_from_login_page(kwargs['response'])
			req.meta['req_once_logged'] = kwargs['req_once_logged']
			req.dont_filter=True


		req.meta['reqtype'] = reqtype   # We tell the type so that we can redo it if login is required
		req.meta['proxy'] = self.proxy  #meta[proxy] is handled by scrapy.

		return req


	def parse(self, response):
		if not self.loggedin(response):
			if self.isloginpage(response):
				if self.logintrial > self.settings['MAX_LOGIN_RETRY']:
					raise Exception("Too many failed login trials. Giving up.")
				self.logger.info("Trying to login.")
				self.logintrial += 1

				yield self.make_request('dologin', req_once_logged=response.request, response=response)

			else:
				inspect_response(response, self)
				raise Exception("Not implemented yet, figure what to do here !")
		else : 
			self.logintrial = 0
			if response.meta['reqtype'] == 'dologin':
				yield response.meta['req_once_logged']

			if response.meta['reqtype'] == 'index':
				for x in self.parse_index(response) : yield x

	def parse_index(self, response):
		# TODO  
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

	def create_request_from_login_page(self, response):
		username_txtbox_list = response.css('.formInputs').xpath('.//label[contains(text(), "Username")]/..').css('input[value=""]')
		password_txtbox_list = response.css('.formInputs').xpath('.//label[contains(text(), "Password")]/..').css('input[value=""]')
		captcha_txt_id = response.css('.formInputs').xpath('.//label[contains(text(), "Captcha code")]').css('::attr(for)').extract_first()

		#The website try to mislead us by adding a bunch of random hidden textbox next to username and password.
		# We aprse css with regex to find which one are hidden.
		
		# Username
		username_txtbox_list2 = []
		style = ''.join(response.css('style').extract())
		for txtbox in username_txtbox_list:
			nodeid = txtbox.xpath("@id").extract_first()
			regex = '#%s\s*\{[^\}]*display\s*:\s*none\s*;[^\}]*\}' % nodeid
			m = re.search(regex, style)
			if not m:
				username_txtbox_list2.append(txtbox)

		#Password
		password_txtbox_list2 = []
		style = ''.join(response.css('style').extract())
		for txtbox in password_txtbox_list:
			nodeid = txtbox.xpath("@id").extract_first()
			regex = '#%s\s*\{[^\}]*display\s*:\s*none\s*;[^\}]*\}' % nodeid
			m = re.search(regex, style)
			if not m:
				password_txtbox_list2.append(txtbox)

		#Success validation
		if len(username_txtbox_list2) != 1:
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

		req = FormRequest.from_response(response, formdata=data)
		req.meta['captcha'] = {		# CaptchaMiddleware will take care of that.
			'request' : self.make_request('captcha_img', response=response),
			'name' : captcha_formname,
			'preprocess' : 'DreamMarketRectangleCropper'	# Preprocess image to extract what's within the rectangle
			}

		return req


