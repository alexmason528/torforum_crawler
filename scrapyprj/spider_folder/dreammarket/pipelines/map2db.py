#This file makes the mapping between a site item and a database PeeWee model.

from scrapy.exceptions import DropItem
import scrapyprj.database.markets.orm.models as dbmodels
from IPython import embed
import scrapyprj.spider_folder.dreammarket.items as items
import hashlib

class map2db(object):

	def __init__(self, *args, **kwargs):
		super(self.__class__, self).__init__(*args, **kwargs)

		self.handlers = {
			items.Ads 		: self.map_ads,
			items.AdsImage 	: self.map_adsimage,
			items.User 		: self.map_user,
			items.ProductRating 		: self.map_product_rating
		}

	def process_item(self, item, spider):	# This function is the one called by Scrapy.
		# THe next pipeline should be scrapyprj.save2db. Sends PeeWee model like this : return {'model' : MyPeeWeeModel}
		for item_type in self.handlers.keys():
			if item_type == type(item):
				return {'model' : self.handlers[item_type].__call__(item,spider)}
		
		raise Exception('Unknown item type : ' + item.__class__.__name__)


	# Mapping functions should be quite similar from spider to spider but may differ.
	# Copy/Paste this code and adjust for differences.

	def map_ads(self, item, spider):
		if type(item) != items.Ads:
			raise Exception("Expecting an item of type items.Ads. Got : " + type(item).__name__ )

		dbads = dbmodels.Ads()

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
		dbads.seller = spider.dao.get_or_create(dbmodels.User,  username= item['vendor_username'], market=spider.market, scrape=spider.scrape) 	# Unique key here
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
			dbimg 			= dbmodels.AdsImage()
			dbimg.ads 		= spider.dao.get_or_create(dbmodels.Ads, external_id = item['ads_id'], market = spider.market)
			dbimg.path 		= image['path']
			dbimg.hash 		= image['checksum']
			dbimg.scrape 	= spider.scrape

			imgs.append(dbimg)

		return imgs

	def map_user(self, item, spider):
		self.drop_if_empty(item, 'username')

		dbuser = dbmodels.User()	# Extended PeeWee object that handles properties in different table
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

		dbfeedback = dbmodels.AdsFeedback()
		dbfeedback.market = spider.market
		dbfeedback.scrape = spider.scrape

		dbfeedback.ads = spider.dao.get_or_create(dbmodels.Ads, external_id = item['ads_id'], market = spider.market)
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

	# Few helpers
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
