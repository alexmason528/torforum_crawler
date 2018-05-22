START TRANSACTION;

insert ignore into `market` (`name`, `spider`) values 
	('Dream Market', 'dreammarket'),
	('Hansa market', 'hansa_market'),
	('Traderoute Market', 'traderoute_market'),
	('Wallstreet Market', 'wallstreet_market'),
	('Darknet Heroes League Market', 'dhl_market'),
	('Cannabis Growers & Merchants Coop', 'cgmc_market'),
	('Libertas Market', 'libertas_market'),
    ('Silk Road', 'silkroad_market'),
    ('French Deep Web Market', 'frenchdeepweb_market'),
    ('Rapture Market', 'rapture_market'),
    ('Olympus Market', 'olympus_market'),
    ('Flugsvamp Market', 'flugsvamp_market'),
    ('Apollon Market', 'apollon_market'),
    ('Berlusconi Market', 'berlusconi_market');

insert ignore into `ads_propkey` (`name`, `prettyname`) values 
	('price', 'Price'),
	('ships_to', 'Ships to'),
	('ships_from', 'Ships from'),
	('escrow', 'Escrow'),
	('description', 'Description'),
	('category', 'Category'),
	('shipping_options', 'Shipping Options'),
	('ships_to_except', 'Ships To Exceptions'),
	('ads_class', 'Class'),
	('in_stock', 'In Stock'),
	('terms_and_conditions', 'Terms & Condition'),
	('refund_policy', 'Refund policy'),
	('stock', 'Stock'),
	('price_options', 'Price Options'),
	('multilisting', 'Multilisting'),
	('multisig', 'Multisignature Available'),
	('views', 'Number of views'),
	('minimum_order', 'Minimum per order'),
	('maximum_order', 'Maximum per order'),
	('already_sold', 'Qty Already Sold'),
	('country', 'Country'),
	('replace_time', 'Replace Time'),
	('auto_accept', 'Auto Accept'),
    ('price_usd', 'Price (USD)'),
    ('price_btc', 'Price (BTC)'),
    ('price_eur', 'Price (EURO)'),
	('price_ltc', 'Price (litecoin)'),
    ('price_bch', 'Price (bitcoin cash)'),
    ('price_xmr', 'Price (monero)'),
	('accepted_currencies', 'Accepted Currencies'),
    ('shipping_time', 'Shipping Time'),
    ('quantity', 'Quantity'),
    ('product_rating', 'Product rating');

insert ignore into `user_propkey` (`name`, `prettyname`) values 
	('successful_transactions', 'Successful Transactions'),
	('average_rating', 'Average Rating'),
	('agora_rating', 'Agora rating'),
	('nucleus_rating', 'Nucleus rating'),
	('alphabay_rating', 'Alphabay rating'),
	('abraxas_rating', 'Abraxas rating'),
	('midlle_earth_rating', 'Middle Earth rating'),
	('hansa_rating', 'Hansa rating'),
	('trusted_seller', 'Trusted seller'),
	('verified','Verified'),
	('fe_enabled', 'Finalize Early Enabled'),
	('join_date', 'Join date'),
	('last_active', 'Last active'),
	('terms_and_conditions', 'Terms and Conditions'),
	('public_pgp_key', 'Public PGP Key'),
	('dreammarket_rating', 'Dream Market Rating'),
	('dreammarket_sales', 'Dream Market Sales'),
	('valhalla_rating', 'Valhalla Rating'),
	('subscribers', 'Subscribers'),
	('positive_feedback', 'Positive Feedback'),
	('neutral_feedback', 'Neutral Feedback'),
	('negative_feedback', 'Negative Feedback'),
	('level', 'Level'),
	('avg_volume', 'Average volume'),
	('profile', 'Profile'),
	('oasis_rating', 'Oasis Rating'),
	('ship_to', 'Shipping To'),
	('ship_from', 'Shipping From'),
	('title', 'Title'),
	('exp', 'Exp'),
	('news', 'News Feed'),
	('successful_transactions_as_buyer', 'Successful Transaction As Buyer'),
	('shipping_information', 'Shipping Information'),
	('forum_posts', 'Forum Posts'),
	('feedback_received', 'Feedback Received'),
	('refund_policy', 'Refund Policy'),
	('reship_policy', 'Reshipping Policy'),
	('average_rating_percernt', 'Average Rating in Percent'),
	('accepted_currencies', 'Accepted Currencies'),
	('badges', 'Badges'),
	('rating_quality', "Rating (Quality)"),
	('rating_speed', "Rating (Speed)"),
	('rating_packaging', "Rating (Packaging)"),
	('rating_communication', "Rating (Communication)"),
	('is_banned', 'Banned'),	
	('has_warning', 'Warning'),	
	('banned_reason', 'Banned reason'),
	('warning_reason', 'Warning reason'),
	('vacation_mode', 'On vacation'),
	('is_buyer', 'Buyer Profile'),
	('successful_orders', 'Successful orders (Buyer)'),
	('unsuccessful_orders', 'Unsuccessful orders (Buyer)'),
	('amount_spent', 'Amount spent (Buyer)'),
	('positive_rating', 'Positive rating (Buyer)'),
	('negative_rating', 'Negative rating (Buyer)'),
	('absolute_rating', 'Absolute rating (Buyer)'),
	('buyer_level', 'Buyer level'),
	('disputes', 'Disputes'),
	('disputes_lost', 'Disputes won'),
	('disputes_draw', 'Disputes lost'),
	('disputes_won', 'Disputes lost'),
	('forum_username', 'Forum username'),
	('irc', 'IRC'),
	('email', 'Email'),
	('icq', 'ICQ'),
	('jabber', 'Jabber (XMPP)'),	
	('website', 'Website'),
	('ricochet', 'Ricochet (IM)'),
	('bitmessage', 'Bitmessage'),
	('btc_address', 'Bitcoin address'),
    ('response_time', 'Response time');

insert ignore into `ads_feedback_propkey` (`name`, `prettyname`) values 
	('submitted_on', 'Submitted on'),
	('submitted_on_string', 'Submitted on (string)'),	
	('item_name', 'Item name'),
	('rating', 'Rating'),
	('comment', 'Comment'),
	('submitted_by','Submitted By'),
	('delivery_time', 'Delivery Time'),
    ('submitter_level', 'Submitter reputation level'),
   	('price', 'Price'),
    ('price_usd', '{Price USD'),
    ('price_xmr', 'Price XMR'),
    ('submitted_by_number_transactions', 'Previous transactions by submitter');

insert ignore into `seller_feedback_propkey` (`name`, `prettyname`) values 
	('submitted_on', 'Submitted on'),
	('submitted_on_string', 'Submitted on (string)'),
	('rating', 'Rating'),
	('comment', 'Comment'),
	('submitted_by','Submitted By'),
	('delivery_time', 'Delivery Time'),
	('communication', 'Communication'),
	('speed', 'Delivery Speed'),
	('stealth', 'Stealth'),
	('quality', 'Quality'),
	('payment_type', 'Payment type'),
	('item_name', 'Item name'),
	('submitter_level', 'Submitter reputation level'),
	('price', 'Price'),
    ('price_usd', 'Price USD'),
    ('price_xmr', 'Price XMR'),
    ('ads_id', 'Ad ID');

COMMIT;