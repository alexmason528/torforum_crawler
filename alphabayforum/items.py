import scrapy

class Thread(scrapy.Item) :
	threadid =  scrapy.Field()
	title =  scrapy.Field()
	author_username =  scrapy.Field()
	last_update =  scrapy.Field()
	relativeurl =  scrapy.Field()
	fullurl =  scrapy.Field()

class Message(scrapy.Item):
	postid = scrapy.Field()
	threadid = scrapy.Field()
	author_username = scrapy.Field()
	posted_on = scrapy.Field()
	contenttext = scrapy.Field()
	contenthtml = scrapy.Field()

class User(scrapy.Item):
	username = scrapy.Field()
	joined_on = scrapy.Field()
	likes_received = scrapy.Field()
	last_activity = scrapy.Field()
	avatar = scrapy.Field()
	message_count = scrapy.Field()
	user_id = scrapy.Field()
	title = scrapy.Field()
	banner = scrapy.Field()
	relativeurl =  scrapy.Field()
	fullurl =  scrapy.Field()