# Spider for Zion Market Forums. These are located on-market and do not foloow the standard board layout.
# Because they are located on-market, vendor profiles can be connected to market data using the relativeurl. 
# Since this data is already present on market, it is not necessary to yield these profiles and collect it.
# Because the board follows a non-standard layout, we don't have typical user profiles. However, some user
# data is available with each post and thread. Namely a link to the user, their member group and their "stars".
# Rasmus is unsure whether stars actually indicate number of transactions, but this may be so. Many users have
# 0 and it seems congruent with vendor sales.
#
# Two bugs are handled in-script. One is a race condition which occurs when Messages and Users are yielded in
# rapid succession. Due to caching, one might reach the DB before the other which returns an error. To avoid 
# this, we sleep for 0.5 seconds between each yield. If you encounter the error where an ID is read from the 
# cache but not DB, try to increase this sleep time.
# Another bug is yielding users without relative urls. Buyers do not have links, and can therefore not be
# yielded with propvals (stars, member group). To do so anyways, we generate non-working URLs for fullurl 
# and relativeurl which are endpoint+username and username.

settings = {
	'timezone' : 'UTC',
	'endpoint' : 'http://zionshopusn6nopy.onion/',
	'prefix' : '',
	'resources' : {
		'index' : "/forum",
		'loginpage' : '/auth/login'
	},

	'logins' : {
		'vivarossa1': {
			'username' : 'vivarossa1',
			'password' : 'pass0000'
		},
		'atomscurl': {
			'username' : 'atomscurl',
			'password' : 'pass0000'
		},
		'malleybono': {
			'username' : 'malleybono',
			'password' : 'pass0000'
		},
		'poseidonsfeet': {
			'username' : 'poseidonsfeet',
			'password' : 'pass0000'
		},
		'ocelotcylinders': {
			'username' : 'ocelotcylinders',
			'password' : 'pass0000'
		}
	}
}