# Some settings specific to a spider.
# The required settings are listed in this template file.

# Copy this file for each spider.

settings = {
	'timezone' : 'GMT',								# Timezone used on the website. 
	'endpoint' : 'http://idcrldul6umarqwi.onion',	# Endpoint of the site. Hostname only
	'prefix' : '',					# http://myhost.onion/prefix1/prefixe2/profix3/page.php
	'resources' : {									# List of availables resources. Url can be created like   self.make_url('MyResource1')  = http://blahblahblah.onion/prefix1/prefix2/section1/page2.php
		'index' : "index.php",
		'loginpage' : "member.php"
		},
	'logins' : {				# Login information. They will be selected in a round robin fashioned when multiple spider is launched at once.
		'vivarossa1': {			# The selected login information is avalaible through  self.login
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
			# 'member\.php\?action\=logout|profile|register|lostpw', # Profile action except login
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
			'/attachment\.php'
		}
	}
}