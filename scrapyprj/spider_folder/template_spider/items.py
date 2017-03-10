import scrapy
# These items define what is available on a website, not the a database object even though they are lookalike.
# A pipeline must convert this item to a PeeWee model to keep flexibility.

# Copy this file for each site to crawl.

class Thread(scrapy.Item) :	
	threadid =  scrapy.Field()
	title =  scrapy.Field()
	author_username =  scrapy.Field()
	last_update =  scrapy.Field()
	relativeurl =  scrapy.Field()
	fullurl =  scrapy.Field()

	Somefield1 = scrapy.Field()
	Somefield2 = scrapy.Field()

class Message(scrapy.Item):
	postid = scrapy.Field()
	threadid = scrapy.Field()
	author_username = scrapy.Field()
	posted_on = scrapy.Field()
	contenttext = scrapy.Field()
	contenthtml = scrapy.Field()

	Somefield1 = scrapy.Field()
	Somefield2 = scrapy.Field()

class User(scrapy.Item):
	username = scrapy.Field()
	relativeurl =  scrapy.Field()
	fullurl =  scrapy.Field()

	Somefield1 = scrapy.Field()
	Somefield2 = scrapy.Field()