import scrapy
# These items define what is available on a website, not the a database object even though they are lookalike.
# A pipeline must convert this item to a PeeWee model to keep flexibility.

# Copy this file for each site to crawl.

class Ads(scrapy.Item) :
	vendor_username = scrapy.Field()
	offer_id = scrapy.Field()
	title = scrapy.Field()
	price = scrapy.Field()
	ships_to = scrapy.Field()	
	ships_from = scrapy.Field()
	escrow = scrapy.Field()	
	description = scrapy.Field()
	category = scrapy.Field()
	shipping_options = scrapy.Field()
	relativeurl = scrapy.Field()
	fullurl = scrapy.Field()

class AdsImage(scrapy.Item):
	ads_id = scrapy.Field()
	image_urls = scrapy.Field()
	images = scrapy.Field()

class User(scrapy.Item) :
	username = scrapy.Field()
	successful_transactions = scrapy.Field()
	average_rating = scrapy.Field()
	agora_rating = scrapy.Field()
	nucleus_rating = scrapy.Field()	
	alphabay_rating = scrapy.Field()
	abraxas_rating = scrapy.Field()
	midlle_earth_rating = scrapy.Field()
	hansa_rating = scrapy.Field()
	trusted_seller = scrapy.Field()
	verified = scrapy.Field()
	fe_enabled = scrapy.Field()
	join_date = scrapy.Field()
	last_active = scrapy.Field()
	terms_and_conditions = scrapy.Field()
	public_pgp_key = scrapy.Field()
	relativeurl = scrapy.Field()
	fullurl = scrapy.Field()
