# Info:
#
# CGMC uses multilisting-type ads. Each ad has a number of sublistings with separate ID's. We collect these and data from them.
# Reviews refer to these ads, so these can be very specific (quantity, etc). We collect feedbacks of type seller and ad from 
# vendor pages (cgmc.onion/SFTreats/comments/132). Reviews that are associated with a still available item are saved as 
# ad_feedbacks while thosoe which are not (typicallly because the item is no longer available) are saved as seller_feedbacks.
#
# For empirical analysis, it is suggested to use ads_feedback and not the both, since a feedback will likely appear in both 
# tables when using multiple crawls in an analysis. If you only use one crawl, then both should be usable.
#
# CGMC can be aggressive in banning us. Since it takes 1-2 days to make a new account, we save some logins that can be used
# in case we get blocked. 
#
# Invite codes:
# http://joincgmc55oplang.onion/zhen5zhocq/
# http://joincgmc55oplang.onion/5r7dydy39k/
# http://joincgmc55oplang.onion/b8130e6n7d/
# http://joincgmc55oplang.onion/jew119vs62/

settings = {
	'timezone' : 'UTC',								# Timezone used on the website. 
	'endpoint' : 'http://cgmcoopwhempo6a5.onion/',	# Endpoint of the site. Hostname only
	'prefix' : '',					# http://myhost.onion/prefix1/prefixe2/profix3/page.php
	'resources' : {									# List of availables resources. Url can be created like   self.make_url('MyResource1')  = http://blahblahblah.onion/prefix1/prefix2/section1/page2.php
		'index' : "/",
		'ads_list' : "/listings/"
		},
	
	'logins' : {				# Login information. They will be selected in a round robin fashioned when multiple spider is launched at once.
		'egotisticgiraffe': {			# The selected login information is avalaible through  self.login
			'username' : 'egotisticgiraffe',
			'password' : 'pass0000'
		},
		'silverwolf' : {
			'username' : 'silverwolf',
			'password' : 'pass0000'
		},
		'marlboroman' : {
			'username' : 'marlboroman',
			'password' : 'pass0000'
		}
	}
}