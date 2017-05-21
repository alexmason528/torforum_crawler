from scrapy.exceptions import DropItem
import scrapyprj.items.forum_items as forum_items
import scrapyprj.items.market_items as market_items
import scrapyprj.database.forums.orm.models as forum_models
import scrapyprj.database.markets.orm.models as market_models
from IPython import embed
import hashlib

class map2db(object):
	def __init__(self, *args, **kwargs):
		super(self.__class__, self).__init__(*args, **kwargs)

		self.handlers = {
			forum_items.Thread 		: self.map_thread,
			forum_items.Message 	: self.map_message,
			forum_items.User 		: self.map_user,
			market_items.Ads 		: self.map_ads,
			market_items.AdsImage 	: self.map_adsimage,
			market_items.User 		: self.map_user,
			market_items.ProductRating 	: self.map_product_rating
		}

	def process_item(self, item, spider):

		for item_type in self.handlers.keys():
			if item_type == type(item):
				return {'model' : self.handlers[item_type].__call__(item,spider)}
		
		raise Exception('Unknown item type : %s' % item.__class__.__name__)


	def map_thread(self, item, spider):
		if type(item) != forum_items.Thread:
			raise Exception("Expecting an item of type forum_items.Thread. Got : " + type(item).__name__ )

		dbthread = forum_models.Thread()

		self.drop_if_empty(item, 'title')
		self.drop_if_empty(item, 'threadid')

		dbthread.forum 		= spider.forum
		dbthread.scrape 	= spider.scrape
		dbthread.title 		= item['title']
		dbthread.external_id= item['threadid']
		dbthread.author = spider.dao.get_or_create(forum_models.User,  username= item['author_username'], forum=spider.forum) # Unique key here
		dbthread.scrape = spider.scrape

		if 'scrape' not in dbthread.author._data or not dbthread.author._data['scrape']: # This could be optimized to be created in get or create above, but that would imply quite a lot of work.
			dbthread.author.scrape=spider.scrape
			dbthread.author.save()

		self.set_if_exist(item, dbthread, 'relativeurl')
		self.set_if_exist(item, dbthread, 'fullurl')
		self.set_if_exist(item, dbthread, 'last_update')
		self.set_if_exist(item, dbthread, 'replies')
		self.set_if_exist(item, dbthread, 'views')

		if not dbthread.author:
			raise DropItem("Invalid Thread : Unable to get User from database. Cannot respect foreign key constraint.")
		elif not dbthread.author.id :
			raise DropItem("Invalid Thread : User foreign key was read from cache but no record Id was available. Cannot respect foreign key constraint")

		return dbthread


	def map_message(self, item, spider):
		if type(item) != forum_items.Message:
			raise Exception("Expecting an item of type forum_items.Message. Got : " + type(item).__name__ )

		dbmsg = forum_models.Message()

		self.drop_if_empty(item, 'author_username')
		self.drop_if_missign(item, 'contenttext')
		self.drop_if_empty(item, 'contenthtml')
		self.drop_if_empty(item, 'threadid')
		self.drop_if_empty(item, 'postid')

		dbmsg.thread = spider.dao.get(forum_models.Thread, forum =spider.forum, external_id = item['threadid'])	#Thread should exist in database
		if not dbmsg.thread:
			raise DropItem("Invalid Message : Unable to get Thread from database. Cannot respect foreign key constraint.")
		elif not dbmsg.thread.id :
			raise DropItem("Invalid Message : Thread foreign key was read from cache but no record Id was available. Cannot respect foreign key constraint")

		dbmsg.forum 	= dbmsg.thread.forum
		dbmsg.scrape 	= spider.scrape
		dbmsg.author 	= spider.dao.get_or_create(forum_models.User, username= item['author_username'], forum=spider.forum) # Make sur only unique key in constructor
		dbmsg.scrape	= spider.scrape
		if 'scrape' not in dbmsg.author._data or not dbmsg.author._data['scrape']: # This could be optimized to be created in get or create above, but that would imply quite a lot of work.
			dbmsg.author.scrape=spider.scrape
			dbmsg.author.save()

		if not dbmsg.author:
			raise DropItem("Invalid Message : Unable to get User from database. Cannot respect foreign key constraint.")
		elif not dbmsg.author.id : # If this happens. Either data is not flush or bug.
			raise DropItem("Invalid Message : Author foreign key was read from cache but no record Id was available. Cannot respect foreign key constraint")

		dbmsg.external_id = item['postid']	
		dbmsg.contenttext = item['contenttext']
		dbmsg.contenthtml = item['contenthtml']
		dbmsg.posted_on = item['posted_on'] if 'posted_on' in item else None
		
		return dbmsg

	def map_user(self, item, spider):
		self.drop_if_empty(item, 'username')

		dbuser = forum_models.User()	# Extended PeeWee object that handles properties in different table
		dbuser.username = item['username']
		
		dbuser.forum = spider.forum
		dbuser.scrape = spider.scrape

		dbuser.setproperties_attribute(scrape = spider.scrape)  #propagate the scrape id to the UserProperty model.

		#Proeprties with same name in model and item
		self.set_if_exist(item, dbuser, 'relativeurl')
		self.set_if_exist(item, dbuser, 'fullurl')

		self.set_if_exist(item, dbuser, 'title')
		self.set_if_exist(item, dbuser, 'location')
		self.set_if_exist(item, dbuser, 'website')
		self.set_if_exist(item, dbuser, 'signature')
		self.set_if_exist(item, dbuser, 'post_count')
		self.set_if_exist(item, dbuser, 'last_post')
		self.set_if_exist(item, dbuser, 'joined_on')
		self.set_if_exist(item, dbuser, 'jabber')
		self.set_if_exist(item, dbuser, 'icq')
		self.set_if_exist(item, dbuser, 'realname')
		self.set_if_exist(item, dbuser, 'microsoft_account')
		self.set_if_exist(item, dbuser, 'yahoo_messenger')

		self.set_if_exist(item, dbuser, 'likes_received')
		self.set_if_exist(item, dbuser, 'last_activity')
		self.set_if_exist(item, dbuser, 'message_count')
		self.set_if_exist(item, dbuser, 'user_id')
		self.set_if_exist(item, dbuser, 'banner')

		self.set_if_exist(item, dbuser, 'membergroup')
		self.set_if_exist(item, dbuser, 'postgroup')
		self.set_if_exist(item, dbuser, 'reputation_power')
		self.set_if_exist(item, dbuser, 'rep_bars')				
		self.set_if_exist(item, dbuser, 'stars')

		self.set_if_exist(item, dbuser, 'karma')
		self.set_if_exist(item, dbuser, 'age')
		self.set_if_exist(item, dbuser, 'group')
		self.set_if_exist(item, dbuser, 'last_active')
		self.set_if_exist(item, dbuser, 'post_per_day')		
		self.set_if_exist(item, dbuser, 'gender')		
		self.set_if_exist(item, dbuser, 'personal_text')		
		self.set_if_exist(item, dbuser, 'custom_title')		

		return dbuser



	def map_ads(self, item, spider):
		if type(item) != market_items.Ads:
			raise Exception("Expecting an item of type items.Ads. Got : " + type(item).__name__ )

		dbads = market_models.Ads()

		#Validation of data.
		self.drop_if_empty(item, 'title')
		self.drop_if_empty(item, 'offer_id')

		#Direct Mapping
		dbads.market 		= spider.market
		dbads.scrape 		= spider.scrape
		dbads.title 		= item['title']
		dbads.external_id	= item['offer_id']	

		if 'relativeurl' in item:
			dbads.relativeurl = item['relativeurl']
		
		if 'fullurl' in item:
			dbads.fullurl 	= item['fullurl']
		
		if 'last_update' in item:	
			dbads.last_update= item['last_update']
		# Link the thread with the user. Request the database (or caching system) to get auto-incremented id.
		dbads.seller = spider.dao.get_or_create(market_models.User,  username= item['vendor_username'], market=spider.market, scrape=spider.scrape) 	# Unique key here
		dbads.scrape = spider.scrape
		
		if not dbads.seller:
			raise DropItem("Invalid Ads : Unable to get User from database. Cannot respect foreign key constraint.")
		elif not dbads.seller.id :
			raise DropItem("Invalid Ads : User foreign key was read from cache but no record Id was available. Cannot respect foreign key constraint")


		self.set_if_exist(item, dbads, 'escrow')
		self.set_if_exist(item, dbads, 'ships_to')
		self.set_if_exist(item, dbads, 'ships_from')
		self.set_if_exist(item, dbads, 'price')
		self.set_if_exist(item, dbads, 'description')
		self.set_if_exist(item, dbads, 'category')
		self.set_if_exist(item, dbads, 'shipping_options')

		dbads.setproperties_attribute(scrape = spider.scrape)


		return dbads	# This object represent a table row. Once it is returned, nothing else should be done.


	def map_adsimage(self, item, spider):
		imgs = []
		for image in item['images']:
			dbimg 			= market_models.AdsImage()
			dbimg.ads 		= spider.dao.get_or_create(market_models.Ads, external_id = item['ads_id'], market = spider.market)
			dbimg.path 		= image['path']
			dbimg.hash 		= image['checksum']
			dbimg.scrape 	= spider.scrape

			imgs.append(dbimg)

		return imgs

	def map_user(self, item, spider):
		self.drop_if_empty(item, 'username')

		dbuser = market_models.User()	# Extended PeeWee object that handles properties in different table
		dbuser.username = item['username']

		if 'relativeurl' in item:
			dbuser.relativeurl = item['relativeurl']
		
		if 'fullurl' in item:
			dbuser.fullurl 	= item['fullurl']
		
		dbuser.market = spider.market
		dbuser.scrape = spider.scrape
		dbuser.setproperties_attribute(scrape = spider.scrape)  #propagate the scrape id to the UserProperty model.

		self.set_if_exist(item, dbuser, 'successful_transactions')
		self.set_if_exist(item, dbuser, 'average_rating')
		self.set_if_exist(item, dbuser, 'agora_rating')
		self.set_if_exist(item, dbuser, 'nucleus_rating')
		self.set_if_exist(item, dbuser, 'alphabay_rating')
		self.set_if_exist(item, dbuser, 'abraxas_rating')
		self.set_if_exist(item, dbuser, 'midlle_earth_rating')
		self.set_if_exist(item, dbuser, 'hansa_rating')
		self.set_if_exist(item, dbuser, 'trusted_seller')
		self.set_if_exist(item, dbuser, 'verified')
		self.set_if_exist(item, dbuser, 'fe_enabled')
		self.set_if_exist(item, dbuser, 'join_date')
		self.set_if_exist(item, dbuser, 'last_active')
		self.set_if_exist(item, dbuser, 'terms_and_conditions')
		self.set_if_exist(item, dbuser, 'public_pgp_key')
		self.set_if_exist(item, dbuser, 'relativeurl')
		self.set_if_exist(item, dbuser, 'fullurl')

		return dbuser

	def map_product_rating(self, item, spider):
		self.drop_if_empty(item, 'rating')

		dbfeedback = market_models.AdsFeedback()
		dbfeedback.market = spider.market
		dbfeedback.scrape = spider.scrape
		found_ads = True
		try:
			dbfeedback.ads = spider.dao.get(market_models.Ads, external_id = item['ads_id'], market = spider.market)
		except market_models.Ads.DoesNotExist :
			raise DropItem("Invalid Ads Feedback : Unable to get Ads from database. Cannot respect foreign key constraint.")

		if not dbfeedback.ads:
			raise DropItem("Invalid Ads Feedback : Unable to get Ads from database. Cannot respect foreign key constraint.")
			
		elif not dbfeedback.ads.id :
			raise DropItem("Invalid Ads Feedback : Ads foreign key was read from cache but no record Id was available. Cannot respect foreign key constraint")

		sha256 = hashlib.sha256()
		sha256.update(str(dbfeedback.ads.id))
		sha256.update(item['rating'])
		sha256.update(item['comment'])
		sha256.update(str(item['submitted_on']))

		dbfeedback.hash = ''.join("{:02x}".format(ord(c)) for c in sha256.digest())

		self.set_if_exist(item, dbfeedback, 'rating')
		self.set_if_exist(item, dbfeedback, 'comment')
		self.set_if_exist(item, dbfeedback, 'submitted_on')
		dbfeedback.setproperties_attribute(scrape = spider.scrape)

		return dbfeedback


	def set_if_exist(self, item, model, field):
		if field in item:
			model.__setattr__(field, item[field])

	def drop_if_missign(self, item, field):
		if field not in item:
			raise DropItem("Missing %s in %s" % (field, item))

	def drop_if_empty(self, item, field):
		self.drop_if_missign(item, field)
		
		if not item[field]:
			raise DropItem("Empty %s in %s" % (field, item))





