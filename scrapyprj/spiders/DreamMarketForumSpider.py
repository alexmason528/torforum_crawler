from __future__ import absolute_import
import scrapy
from scrapy.http import FormRequest,Request
from scrapy.shell import inspect_response
from scrapyprj.spiders.ForumSpiderV3 import ForumSpiderV3
from scrapyprj.database.orm import *
import scrapyprj.database.forums.orm.models as models
import scrapyprj.items.forum_items as items
from datetime import datetime, timedelta
from urlparse import urlparse, parse_qsl
import logging
import time
import hashlib 
import traceback
import re
import pytz
import dateutil
from IPython import embed
from random import randint


class DreamMarketForumSpider(ForumSpiderV3):
	name = "dreammarket_forum"  
	custom_settings = {
		'MAX_LOGIN_RETRY' : 10,
		'RANDOMIZE_DOWNLOAD_DELAY' : True
	}

	def __init__(self, *args, **kwargs):
		super(DreamMarketForumSpider, self).__init__(*args, **kwargs)

		self.set_max_concurrent_request(1)      # Scrapy config
		self.set_download_delay(10)              # Scrapy config
		self.set_max_queue_transfer_chunk(1)    # Custom Queue system
		self.statsinterval = 60 				# Custom Queue system
		self.logintrial = 0						# Max login attempts.
		self.alt_hostnames = []					# Not in use.
		self.report_status = False				# Report 200's.
		self.loggedin = False					# Login flag. 

	def start_requests(self):
		yield self.make_request(url = 'index', dont_filter=True)

	def make_request(self, reqtype='regular', **kwargs):
		if 'url' in kwargs:
			kwargs['url'] = self.make_url(kwargs['url'])
		# Handle the requests.
		# If you need to bypass DDoS protection, put it in here.
		if reqtype is 'dologin':
			req = self.craft_login_request_from_form(kwargs['response']) 
			req.dont_filter = True
		elif reqtype is 'loginpage':
			req = Request(self.make_url('loginpage'), dont_filter=True, headers = self.tor_browser)
		elif reqtype is 'regular':
			req = Request(kwargs['url'], headers = self.tor_browser)
			req.meta['shared'] = True # Ensures that requests are shared among spiders.
		# Some meta-keys that are shipped with the request.
		if 'relativeurl' in kwargs:
			req.meta['relativeurl'] = kwargs['relativeurl']
		if 'dont_filter' in kwargs:
			req.dont_filter = kwargs['dont_filter']
		if 'req_once_logged' in kwargs:
			req.meta['req_once_logged'] = kwargs['req_once_logged']  
		req.meta['proxy'] = self.proxy  
		req.meta['slot'] = self.proxy

		return self.set_priority(req)

	def parse_response(self, response):
		parser = None
		# Handle login status.
		if self.islogged(response) is False:
			self.loggedin = False
			if self.is_login_page(response) is False:
				# req_once_logged stores the request we will go to after logging in.
				req_once_logged = response.request
				yield self.make_request(reqtype='loginpage',response=response, req_once_logged=req_once_logged) 
			else:
				req_once_logged = response.meta['req_once_logged'] if 'req_once_logged'  in response.meta else response.request
				# Try to yield informative error messages if we can't logon.
				if self.is_login_page(response) is True and self.login_failed(response) is True:
					self.logger.info('Failed last login. Trying again. Error: %s' % self.get_text(response.xpath('.//div/ul[@class="error-list"]')))
				# Allow the spider to fail if it can't log on.
				if self.logintrial > self.settings['MAX_LOGIN_RETRY']:
					self.wait_for_input("Too many login failed", req_once_logged)
					self.logintrial = 0
					return
				self.logger.info("Trying to login as %s." % self.login['username'])
				self.logintrial += 1
				yield self.make_request(reqtype='dologin', response=response, req_once_logged=response.meta['req_once_logged'])
		# Handle parsing.
		else:
			# Notify on succesful login and set parsing flag.
			if 'req_once_logged' in response.meta and self.loggedin is False:
				self.logger.info("Succesfully logged in as %s! Returning to stored reguest %s" % (self.login['username'], response.meta['req_once_logged']))
				yield response.meta['req_once_logged']
				self.loggedin = True
			# Parsing handlers.
			# A simple function designates whether a page should be parsed.
			if self.is_threadlisting(response) is True:
				parser = self.parse_threadlisting
			elif self.is_message(response) is True:
				parser = self.parse_message
			elif self.is_user(response) is True:
				parser = self.parse_user
		# Yield the appropriate parsing function.
		if parser is not None:
			for x in parser(response):
				yield x

	########## PARSING FLAGS ##############
	def is_message(self, response):
		if "viewtopic.php?id=" in response.url:
			return True

	def is_user(self, response):
		if 'profile.php?id=' in response.url:
			return True

	def is_threadlisting(self, response):
		if "viewforum.php?id=" in response.url:
			return True
	########## PARSING FUNCTIONS ##########
	def parse_user(self, response):
		user = items.User()
		user['relativeurl'] = self.get_relative_url(response.url)
		user['fullurl'] = response.url

		dts = response.css("#viewprofile dl dt")

		for dt in dts:
			key = self.get_text(dt).lower()
			ddtext = self.get_text(dt.xpath('following-sibling::dd[1]'))

			if key == 'username':
				user['username'] = ddtext
			elif key == 'title':
				user['title'] = ddtext
			elif key == 'registered':
				user['joined_on'] = self.parse_datetime(ddtext)
			elif key == 'last post':
				user['last_post'] = self.parse_datetime(ddtext)
			elif key == 'posts':
				m = re.match("^(\d+).+", ddtext)
				if m:
					user['post_count'] = m.group(1)
			elif key == 'signature':
				user['signature'] = ddtext
			elif key == 'location':
				user['location'] = ddtext
			elif key == 'jabber':
				user['jabber'] = ddtext
			elif key == 'icq':
				user['icq'] = ddtext
			elif key == 'real name':
				user['realname'] = ddtext
			elif key == 'microsoft account':
				user['microsoft_account'] = ddtext            
			elif key == 'yahoo! messenger':
				user['yahoo_messenger'] = ddtext
			elif key == 'website':
				user['website'] = ddtext
			elif key in ['avatar', 'email', 'pm']:
				pass
			else:
				self.logger.warning('New information found on use profile page : %s' % key)

			yield user

	def parse_message(self, response):
		threadid 		= self.get_url_param(response.url, 'id')
		posts 			= response.css("#brdmain div.blockpost")
		index 			= 0
		last_posttime 	= None
		authors 		= posts.xpath(".//div[@class='postleft']/dl/dt/strong/a/text()").extract()
		for post in posts:
			try:
				messageitem 					= items.Message()
				userprofile_link 				= post.css(".postleft dt:first-child a::attr(href)").extract_first()
				messageitem['author_username']  = self.get_text(post.xpath(".//div[@class='postleft']/dl/dt/strong/a/text()").extract_first())
				# The admin (SpeedStepper) obfuscates/spoofs their time of posting. 
				# Their posts are therefore tagged as coming *just before* the proceding post.
				# SpeedStepper frequently makes 2+ posts in a row, so we need to hack around a bit.
				# a while-loop would be better.
				only_admin = len(list(set(authors))) == 1 and list(set(authors))[0] == 'SpeedStepper'
				if only_admin is True:
					posttime 	= None
					self.logger.warning("Only SpeedStepper has posted in this thread. No posted_on could be determined from %s." % response.url)
				elif messageitem['author_username'] == 'SpeedStepper' and index == 0:
					if self.get_text(posts[index + 1].xpath("h2/span/a/text()").extract_first()) == '':
						posttime 			= self.parse_datetime(self.get_text(posts[index + 2].xpath("h2/span/a/text()").extract_first())) - timedelta(seconds=2)	
					else:
						posttime 			= self.parse_datetime(self.get_text(posts[index + 1].xpath("h2/span/a/text()").extract_first())) - timedelta(seconds=1)
					last_posttime = posttime # A failsafe ensuring we always have a time we can refer to and accomodate SpeedStepper.
				elif messageitem['author_username'] == 'SpeedStepper' and index > 0 and last_posttime is not None:
					posttime 				= last_posttime + timedelta(seconds=1)
					last_posttime = posttime # A failsafe ensuring we always have a time we can refer to and accomodate SpeedStepper.
				else:
					posttime 				= self.parse_datetime(self.get_text(post.xpath("h2/span/a/text()").extract_first()))
					last_posttime = posttime # A failsafe ensuring we always have a time we can refer to and accomodate SpeedStepper.
				messageitem['posted_on'] 	= posttime
				messageitem['postid'] 		= post.xpath("@id").extract_first()
				messageitem['threadid'] 	= threadid
				#messageitem['subforum'] = self.get_text(response.css('ul.crumbs:nth-child(2) > li:nth-child(2) > a:nth-child(2)'))
				#self.logger.info("subforum is %s" % messageitem['subforum'])
				msg 					    = post.css("div.postmsg")
				messageitem['contenttext']  = self.get_text(msg)
				messageitem['contenthtml']  = self.get_text(msg.extract_first())
				index = index + 1
				yield messageitem
			except Exception as e:
				self.logger.warning("Invalid thread page at %s (Error: '%s'" % (response.url, e))

	def parse_threadlisting(self, response):
		for line in response.css("#brdmain tbody tr"):
			threaditem 						= items.Thread()
			title 							=  self.get_text(line.css("td:first-child a"))         
			threadlinkobj 					= next(iter(line.css("td:first-child a") or []), None) # First or None if empty
			if line.xpath(".//span[@class='movedtext']"):
				self.logger.warning("Thread was moved. Not collected.")
			elif threadlinkobj:
				last_post_time 				= self.parse_datetime(self.get_text(line.css("td:last-child a")))  
				threadlinkhref 				= threadlinkobj.xpath("@href").extract_first() if threadlinkobj else None
				threaditem['title'] 		= self.get_text(threadlinkobj)
				if threaditem['title'] == '':
					threaditem['title'] 	= "[Untitled thread]"
					self.logger.warning("Encountered a thread with no title at %s. Inserted %s as title." % (response.url, threaditem['title']))
				threaditem['relativeurl'] 	= threadlinkhref
				threaditem['fullurl']   	= self.make_url(threadlinkhref)             
				threaditem['threadid'] 		= self.get_url_param(threaditem['fullurl'], 'id')
				byuser 						= self.get_text(line.css("td:first-child span.byuser"))
				m = re.match("by (.+)", byuser) # regex
				if m:
					threaditem['author_username'] = m.group(1)
				threaditem['last_update'] 	= last_post_time
				threaditem['replies']   	= self.get_text(line.css("td:nth-child(2)"))
				threaditem['views']     	= self.get_text(line.css("td:nth-child(3)"))
			else:
				self.logger.warning("no threadlinkobj")
			yield threaditem


	############ LOGIN HANDLING ################
	def login_failed(self, response):
		if len(response.xpath('.//div/ul[@class="error-list"]')) > 0:
			return True

	def islogged(self, response):
		contenttext = self.get_text(response.css("#brdwelcome"))
		if 'Logged in as' in contenttext:
			return True
		return False

	def is_login_page(self, response):
		if len(response.css("form#login")) > 0:
			return True
		return False

	def craft_login_request_from_form(self, response):
		data = {
			'req_username' : self.login['username'],
			'req_password' : self.login['password']
		}
		req = FormRequest.from_response(response, formdata=data, headers = self.tor_browser)

		captcha_src = response.css("form#login img::attr(src)").extract_first()

		req.meta['captcha'] = {        # CaptchaMiddleware will take care of that.
			'request' : self.make_request(url=captcha_src, dont_filter = True, priority = 10),
			'name' : 'inpcaptch',    # Preprocess image to extract what's within the rectangle
			'preprocess' : 'DreamMarketRectangleCropper'
			}
		req.dont_filter = True
		return req

	########### MISCELLANEOUS ###################
	# def parse_timestr(self, timestr):
	# 	last_post_time = None
	# 	try:
	# 		timestr = timestr.lower()
	# 		timestr = timestr.replace('today', str(self.localnow().date()))
	# 		timestr = timestr.replace('yesterday', str(self.localnow().date() - timedelta(days=1)))
	# 		last_post_time = self.to_utc(dateutil.parser.parse(timestr))
	# 	except:
	# 		if timestr:
	# 			self.logger.warning("Could not determine time from this string : '%s'. Ignoring" % timestr)
	# 	return last_post_time