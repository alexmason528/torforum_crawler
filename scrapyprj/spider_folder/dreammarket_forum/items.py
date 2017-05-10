import scrapy
class Thread(scrapy.Item) :
	threadid =  scrapy.Field()
	title =  scrapy.Field()
	author_username =  scrapy.Field()
	last_update =  scrapy.Field()
	relativeurl =  scrapy.Field()
	fullurl =  scrapy.Field()
	replies = scrapy.Field()
	views = scrapy.Field()

class Message(scrapy.Item):
	postid = scrapy.Field()
	threadid = scrapy.Field()
	author_username = scrapy.Field()
	posted_on = scrapy.Field()
	contenttext = scrapy.Field()
	contenthtml = scrapy.Field()

class User(scrapy.Item):
	username = scrapy.Field()
	relativeurl =  scrapy.Field()
	fullurl =  scrapy.Field()
	
	title = scrapy.Field()
	location = scrapy.Field()
	website = scrapy.Field()
	signature = scrapy.Field()
	post_count = scrapy.Field()
	last_post = scrapy.Field()
	joined_on = scrapy.Field()