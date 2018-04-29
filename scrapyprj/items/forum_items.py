import scrapy
class Thread(scrapy.Item) :
	threadid =  scrapy.Field() # Unique value. This is the website ID that references the THREAD in which you find the MESSAGE.
	title =  scrapy.Field()
	author_username =  scrapy.Field()
	last_update =  scrapy.Field()
	relativeurl =  scrapy.Field()
	fullurl =  scrapy.Field()
	replies = scrapy.Field()
	views = scrapy.Field()

class Message(scrapy.Item):
	postid = scrapy.Field() # Unique value. This is the website ID that references the POST found in the THREAD. You typically find this in HTML.
	threadid = scrapy.Field() # Unique value. This is the website ID that references the THREAD in which you find the MESSAGE. 
	author_username = scrapy.Field()
	posted_on = scrapy.Field()
	contenttext = scrapy.Field()
	contenthtml = scrapy.Field()

class User(scrapy.Item):
	# Base identifiers.
	username = scrapy.Field()
	relativeurl =  scrapy.Field()
	fullurl =  scrapy.Field()
	username_id = scrapy.Field() # Is a propval. It shouldn't be relevant for DB structure and yielding.
	
	# Presentation.
	age = scrapy.Field()
	avatar = scrapy.Field()
	banner = scrapy.Field()	
	birthday = scrapy.Field()
	custom_title = scrapy.Field()
	group = scrapy.Field()
	gender = scrapy.Field()
	location = scrapy.Field()
	membergroup = scrapy.Field()
	occupation = scrapy.Field()
	personal_text = scrapy.Field()
	postgroup = scrapy.Field()
	realname = scrapy.Field()
	rank = scrapy.Field() # Use when there is a specific field referencing this value.
	signature = scrapy.Field()
	title = scrapy.Field()	
	website = scrapy.Field()

	# Behavior.
	post_count = scrapy.Field() # This is the number of what we call threads.
	last_post = scrapy.Field()
	joined_on = scrapy.Field()
	last_activity = scrapy.Field()
	last_active = scrapy.Field() # Deprecated, do not use.
	post_per_day = scrapy.Field()
	message_count = scrapy.Field() # These are what we call messages. They are replies to threads.

	# Communication options.
	icq = scrapy.Field()
	microsoft_account = scrapy.Field()
	jabber = scrapy.Field()
	yahoo_messenger = scrapy.Field()
	email = scrapy.Field()
	msn = scrapy.Field()
	pgp_key = scrapy.Field()
	aol = scrapy.Field()

	# Reputation and acknowledgement.
	average_rating = scrapy.Field()
	followers = scrapy.Field()
	karma = scrapy.Field()
	likes_received = scrapy.Field()
	rating_count = scrapy.Field()
	reputation_power = scrapy.Field() # Use when it is calles reputation power.
	rep_bars = scrapy.Field() # Use when it is called reputation bars or described as such.
	reputation = scrapy.Field() # Use when reputation called reputation and a numeric score.
	stars = scrapy.Field()
	trophy_points = scrapy.Field()
	user_sales = scrapy.Field() # Use when there is a number of transactions assigned for a seller.
	user_buys  = scrapy.Field() # Use when there is a number of transactions assigned for a buyer.
	awards = scrapy.Field()
