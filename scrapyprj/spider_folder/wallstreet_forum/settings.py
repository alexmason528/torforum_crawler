# Some settings specific to a spider.
# The required settings are listed in this template file.

# Copy this file for each spider.

settings = {
	'timezone' : 'UTC',								# Timezone used on the website. 
	'endpoint' : 'http://x7bwsmcore5fmx56.onion/',	# Endpoint of the site. Hostname only
	'prefix' : '',					# http://myhost.onion/prefix1/prefixe2/profix3/page.php
	'resources' : {									# List of availables resources. Url can be created like   self.make_url('MyResource1')  = http://blahblahblah.onion/prefix1/prefix2/section1/page2.php
		'index' : "/index.php",
		'login' : "/login.php"
		},
	'logins' : {				# Login information. They will be selected in a round robin fashioned when multiple spider is launched at once.
		'poseidonsfeet': {			# The selected login information is avalaible through  self.login
			'username' : 'poseidonsfeet',
			'password' : 'pass0000'
		}
	},
	# Exclude lists for URIs that we shouldn't visit
	'exclude' : {
		'prefix' : { # Prefix exclude like '/account/' everything like '/account/logout' or '/account/settings' will be excluded
			'/search.php',
			'/login.php?action=out',
			'/signup.php',
			'/extern.php'
		},
		'regex' : { # Regex prefixes, ran against the url part that comes after '.onion/'
			#'/discussion/\d+/comment/reply/',
			#'/discussion/\d+/comment/quote/'
		}
	}
}