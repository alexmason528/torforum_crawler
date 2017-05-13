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

	icq = scrapy.Field()
	realname = scrapy.Field()
	microsoft_account = scrapy.Field()
	jabber = scrapy.Field()
	yahoo_messenger = scrapy.Field()


	likes_received = scrapy.Field()
	last_activity = scrapy.Field()
	avatar = scrapy.Field()
	message_count = scrapy.Field()
	user_id = scrapy.Field()
	banner = scrapy.Field()	