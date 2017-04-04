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
	relative_url = scrapy.Field()
	full_url = scrapy.Field()
