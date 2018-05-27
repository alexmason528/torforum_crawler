# When you work with markets it is very important that you give a lot of consideration
# and are thorough about what you yield them as. If you have any questions, send Rasmus
# a ping on basecamp. 
#
# The best way to go about it, is to find a good and informative example page for an item.
# Usually a popular product or vendor is a good place to start. Then go through the list 
# of scrapy.Fields(), and see how many you can fill out from the page. Remember, if there 
# are new fields, you should tell us about it so we can add them! This is VERY important.

import scrapy

# The Ads-Item class is for advertisements of products. For example, 1 gram of cannabis,
# 1 ebook on crime and so forth.  These are fetched from the LISTING or ITEM page. Do not
# mix them up with similar fields but for vendors. 
class Ads(scrapy.Item) :
	# Base identifiers.
	# These are some general identifiers.
	vendor_username 	= scrapy.Field() # The username of the vendor/seller.
	offer_id			= scrapy.Field() # The website's ID of the product. Typically found in the URL.
	title 				= scrapy.Field() # The product title.
	relativeurl 		= scrapy.Field() # The relative URL. For example, /item?id=928 
	fullurl 			= scrapy.Field() # The complete URL. For example, website.onion/item?id=928
	# Multilisting are when an item has "sub-items". For example, on one website a product has the ID /9ad/. 
	# When looking at the ad, the programmer sees that there are four extra ads with the same product. The
	# difference is their offer_id's, which are /2dh/, 3kk/ and so forth. It is VERY important we collect
	# these correctly. If you see them, send Rasmus a ping to discuss how to collect them.
	multilisting 		= scrapy.Field() 

	# Pricing.
	# Prices are set in dollars, but people pay with crypto currencies like bitcoin.
	# We want to collect both prices.
	price 				= scrapy.Field() # The original price field. Now deprecated. If a spider still uses it, convert to one of the others.
	price_options 		= scrapy.Field() # Some websites will have options like 1 gram/5 grams/1 kilo. If it is NOT a multilisting, we store the values here.
	escrow 				= scrapy.Field() # Escrow, Finalize Early and 50/50 Escrow/Early finalization are typically seen. 
	multisig 			= scrapy.Field() # Is the item advertised as a "Multisignature" payment?
	price_usd 			= scrapy.Field() # The price in US Dollars.
	price_eur			= scrapy.Field()
	price_btc			= scrapy.Field()
	price_ltc			= scrapy.Field() # The price in Litecoin (LTC)
	price_bch 			= scrapy.Field() # The price in Bitcoin Cash (BCH)
	price_xmr 			= scrapy.Field() # The price on Monero (XMR)
	accepted_currencies = scrapy.Field() # If you can pay for a product with different crypto currencies, include them like such: "XMR, BTC, LTC".

	# Product information.
	# These fields are about the product.
	description 		 = scrapy.Field() 	 
	terms_and_conditions = scrapy.Field()
	refund_policy		 = scrapy.Field()
	category 			 = scrapy.Field() # You do not need to add category.
	ships_to 			 = scrapy.Field()
	ships_to_except 	 = scrapy.Field() # Some markets will have a separate field with countries you cannot order the product to.
	ships_from 			 = scrapy.Field()
	shipping_options 	 = scrapy.Field() # This is for example, a dropdown field where you can choose between "Express shipping" and "Standard shipping"
	ads_class 			 = scrapy.Field() 
	in_stock 			 = scrapy.Field() 
	stock 				 = scrapy.Field()
	views 				 = scrapy.Field()
	minimum_order 		 = scrapy.Field()
	maximum_order 		 = scrapy.Field()
	already_sold 		 = scrapy.Field()
	country 			 = scrapy.Field()
	replace_time 		 = scrapy.Field()
	auto_accept 		 = scrapy.Field()
	shipping_time 		 = scrapy.Field()
	quantity 			 = scrapy.Field()
	product_rating 		 = scrapy.Field() # Use when there is a total rating of the product.

# This class is for collecting images.
# See how other crawlers handle them.
class AdsImage(scrapy.Item):
	ads_id 		= scrapy.Field()
	image_urls  = scrapy.Field()
	images 		= scrapy.Field()

# This class is for Users, which means sellers or vendors. NOT buyers.
# Not all markets will have all of these. They will have a few. But we
# want as many of them as possible. Sometimes more information can be
# found on the vendor's product. Do not parse those pages to yield 
# User items. We can just join datasets. This class if for information
# on the seller/vendor's profile page.
class User(scrapy.Item) :
	# Base identifiers.
	username 	= scrapy.Field()
	relativeurl = scrapy.Field()
	fullurl 	= scrapy.Field()

	
	# These six fields are ONLY used for buyer profiles.
	is_buyer						 = scrapy.Field() # Sometimes we will need to collect buyers as users. In that case it is VERY important to note they are buyers.
	successful_orders				 = scrapy.Field()
	unsuccessful_orders 			 = scrapy.Field()
	amount_spent 					 = scrapy.Field()
	positive_rating					 = scrapy.Field()
	negative_rating					 = scrapy.Field()
	buyer_level 					 = scrapy.Field()
	absolute_rating 				 = scrapy.Field() # Used when there is a 4.5/5 or 95%-like field. that is, an average rating.
	buyer_profile					 = scrapy.Field()
	buyer_country					 = scrapy.Field()

	# Ratings from other markets.
	agora_rating 					 = scrapy.Field()
	nucleus_rating  				 = scrapy.Field()	
	alphabay_rating 				 = scrapy.Field()
	abraxas_rating  				 = scrapy.Field()
	midlle_earth_rating				 = scrapy.Field()
	hansa_rating 					 = scrapy.Field()
	dreammarket_rating 				 = scrapy.Field()
	dreammarket_sales				 = scrapy.Field()
	valhalla_rating 				 = scrapy.Field()
	oasis_rating 				 	 = scrapy.Field()

	# Ratings and behavior on this market.
	feedback_received 				 = scrapy.Field()
	positive_feedback 				 = scrapy.Field()
	neutral_feedback 				 = scrapy.Field()
	negative_feedback 				 = scrapy.Field()
	successful_transactions 		 = scrapy.Field() 
	average_rating 					 = scrapy.Field() # When the average rating is a 0-5 or 1-5 scale.
	average_rating_percent  		 = scrapy.Field() # For when average ratings are presented on a scale from 0-100%
	avg_volume 						 = scrapy.Field()
	exp 							 = scrapy.Field()
	level 							 = scrapy.Field() # Distinguish between "Level" and Trust level.
	trust_level						 = scrapy.Field()
	rating_quality			     	 = scrapy.Field()
	rating_speed		 			 = scrapy.Field()
	rating_packaging				 = scrapy.Field()
	rating_communication 			 = scrapy.Field()
	rating_shipping					 = scrapy.Field()
	disputes 						 = scrapy.Field() # Used if there is just 1 dispute number. If there are more details, use the following 3.
	disputes_won					 = scrapy.Field()
	disputes_draw					 = scrapy.Field()
	disputes_lost					 = scrapy.Field()

	# Presentation of the vendor.
	trusted_seller 					 = scrapy.Field()
	verified 						 = scrapy.Field()
	fe_enabled 						 = scrapy.Field()
	member_class					 = scrapy.Field()
	terms_and_conditions			 = scrapy.Field()
	public_pgp_key 					 = scrapy.Field()
	badges 							 = scrapy.Field() # A catch all for lists with badges such as "Good communication", "Quality vendor" etc.
	forum_username					 = scrapy.Field() # Used if the user has an associated name on the marketplace forum.
	irc								 = scrapy.Field() # Bitmessage IRC, email and ricochet should only be added if there are specific fields for them.
	email							 = scrapy.Field() # Do not parse regular text to get them.
	ricochet						 = scrapy.Field()
	icq								 = scrapy.Field()
	jabber							 = scrapy.Field()
	website 						 = scrapy.Field()
	bitmessage						 = scrapy.Field()
	btc_address						 = scrapy.Field()
	verification_process			 = scrapy.Field()

	# Information about the vendor.
	join_date  				         = scrapy.Field()
	last_active 					 = scrapy.Field()
	response_time	 				 = scrapy.Field()
	vacation_mode					 = scrapy.Field() # Return True if the vendor's profile says they are on vacation.
	subscribers 					 = scrapy.Field()
	profile 						 = scrapy.Field() # Profile text.
	title 					         = scrapy.Field()
	successful_transactions_as_buyer = scrapy.Field() # Used when a vendor also has purchased as a buyer.
	news 							 = scrapy.Field()
	is_banned 						 = scrapy.Field() # A True/False value if the vendor is banned.
	banned_reason 					 = scrapy.Field() # A string containing the reason for the ban.
	has_warning 					 = scrapy.Field() # A True/False value if the vendor profile has a warning.
	warnings_number					 = scrapy.Field()
	warning_reason 					 = scrapy.Field() # A string containing the reason why there is a warning.

	# Business details:
	forum_posts  					 = scrapy.Field()
	ship_from 	  					 = scrapy.Field()
	ship_to 	 					 = scrapy.Field()
	refund_policy					 = scrapy.Field()
	reship_policy					 = scrapy.Field()
	shipping_information			 = scrapy.Field()
	accepted_currencies				 = scrapy.Field()


# We have two classes of Ratings we collect. One uses the SELLER as an identifier (username),
# and the other uses the item. If the item can be identified from a review, it is a ProductRating.
# If not, it is a UserRating.

# Product Rating Items are the reviews found on product pages. 
class ProductRating(scrapy.Item):
	# Base identifiers.
	ads_id 							 = scrapy.Field() # The ID of the ad.
	submitted_by 					 = scrapy.Field() # The username of the submitter.
	item_name 						 = scrapy.Field() # This is especially useful, if you can read from the review what quantity was purchased.

	# Transaction information:
	submitted_on 					 = scrapy.Field() # The date on which the raview was posted/submitted.
	submitted_on_string 			 = scrapy.Field() # submitted_on but as a string. Used for data validation.
	delivery_time 		 			 = scrapy.Field() # Time to delivery (if shown)
	price_usd 			 		 	 = scrapy.Field() # The price in USD.
	price_xmr 			 			 = scrapy.Field() # The price in XMR.
	submitter_level 				 = scrapy.Field() # The level of the submitter.
	submitted_by_number_transactions = scrapy.Field()
	submitter_rating				 = scrapy.Field() # Used when the reviewer has a reputation score. Typically a small number.

	# Ratings:
	rating 							 = scrapy.Field() # The rating.
	comment 						 = scrapy.Field() # The comment.
	
# User Rating Items are reviews on the page of the SELLER or VENDOR.
class UserRating(scrapy.Item):
	# Base identifiers.
	submitted_on 		= scrapy.Field()
	submitted_on_string = scrapy.Field()
	username 			= scrapy.Field() # This is the username of the seller, NOT the buyer.
	submitted_by 		= scrapy.Field() # This is the username of the buyer.
	item_name 			= scrapy.Field()
	ads_id				= scrapy.Field()

	# Transaction information:
	# Price fields are used when there is a specific price associated with the review.
	# Otherwise, we refer to ads when estimating the price of an item. They are ONLY
	# collected when the review has a price next to it.
	delivery_time 		= scrapy.Field()
	payment_type 		= scrapy.Field()
	submitter_level 	= scrapy.Field() 
	price 				= scrapy.Field() # Deprecated. Always include the currency.
	price_usd 			= scrapy.Field()
	price_xmr			= scrapy.Field()
	submitted_on_string = scrapy.Field()
	submitted_by_number_transactions = scrapy.Field()
	submitter_rating				 = scrapy.Field() # Used when the reviewer has a reputation score. Typically a small number.

	# Ratings:
	comment 			= scrapy.Field()
	rating 				= scrapy.Field()
	speed 				= scrapy.Field()
	stealth 			= scrapy.Field()
	quality 			= scrapy.Field()
	communication 		= scrapy.Field()

