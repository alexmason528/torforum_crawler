# IDC 2.0 is an italian language forum. It dates back to at least 2014. There are no particularities regarding the spider,
# or data observed.
#
# It is noted, that to properly collect guest users we must collect them with dummy-urls. Relative and full URLs are 
# generated using the username and the URL. Further, Joined on is collected as a string, because parsing italian dates
# is not ideal without thorough control.


settings = {
	'timezone' : 'GMT',			
	'endpoint' : 'http://idcrldul6umarqwi.onion',	
	'prefix' : '',			
	'resources' : {			
		'index' : "index.php",
		'loginpage' : "member.php"
		},
	'logins' : {			
		'vivarossa1': {		
			'username' : 'vivarossa1',
			'password' : 'pass0000'
		},
		'happyhippo': {
			'username': 'happyhippo',
			'password': 'pass0000'
		},
		'nevergonnagive': {
			'username': 'nevergonnagive',
			'password': 'pass0000'
		},
		'PLAYSOMETHINGWITHSLAYER': {
			'username': 'PLAYSOMETHINGWITHSLAYER',
			'password': 'pass0000'
		},
		'distill3r': {
			'username': 'distill3r',
			'password': 'pass0000'
		}
	},
	# Exclude lists for URIs that we shouldn't visit
	'exclude' : {
		'prefix' : { # Prefix exclude like '/account/' everything like '/account/logout' or '/account/settings' will be excluded
		},
		'regex' : { # Regex prefixes, ran against the url part that comes after '.onion/'
			'.*\#.*', # Links to individual posts
			'.*sortby.*', # Thread sorting links
			'.*lastpost.*', # Links to last post
			'.*nextoldest|nextnewest.*', # previous/next thread
			'/loginpage',
			'/javascript',
			'/mailto',
			'/private.php',
			'/misc.php', # action=help|markread|syndication
			'/usercp.php',
			'/usercp2.php',
			'/newthread.php',
			'/search.php',
			'/archive/',
			'/ratethread.php',
			'/reputation.php',
			'/newreply.php',
			'/printthread.php',
			'/showteam.php',
			'/stats.php',
			'/online.php',
			'/awards.php',
			'/portal.php',
			'/member.php',
			'/archive',
			'/attachment\.php',
			'\.png$'
		}
	},
	'priority': {
		'thread': {
			'regex': 'showthread\.php\?tid=',
			'value': -1
		},
		'message': {
			'regex': 'forumdisplay\.php\?fid=',
			'value': -2
		}
	}
}