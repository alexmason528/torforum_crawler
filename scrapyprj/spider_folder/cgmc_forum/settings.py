# Some settings specific to a spider.
# The required settings are listed in this template file.

# Copy this file for each spider.

# Invites:
# http://joincgmc55oplang.onion/sep7v2osf5/
# http://joincgmc55oplang.onion/0x6bwi2dkx/
# http://joincgmc55oplang.onion/ix03xrjk0x/

settings = {
	'timezone' : 'UTC',								# Timezone used on the website. 
	'endpoint' : 'http://forum.cgmcoopwhempo6a5.onion/',	# Endpoint of the site. Hostname only
	'prefix' : '',					# http://myhost.onion/prefix1/prefixe2/profix3/page.php
	'resources' : {									# List of availables resources. Url can be created like   self.make_url('MyResource1')  = http://blahblahblah.onion/prefix1/prefix2/section1/page2.php
		'index' : "/"
		},
	
	'logins' : {		# Login information. They will be selected in a round robin fashioned when multiple spider is launched at once.
		'malleybono': { # The selected login information is avalaible through  self.login
			'username' : 'malleybono',
			'password' : 'pass0000'
		}
	},
	# Exclude lists for URIs that we shouldn't visit
	'exclude' : {
		'prefix' : { # Prefix exclude like '/account/' everything like '/account/logout' or '/account/settings' will be excluded
			'/login',
			'/blogs/',
			'/account/',
			'/forum/create',
			'/forum/vote',
			'/forum/report_comment/',
			'/forum/subscribe/',
			'/forum/toggle_subscription/'
		},
		'regex' : { # Regex prefixes, ran against the url part that comes after '.onion/'
			'/discussion/\d+/comment/reply/',
			'/discussion/\d+/comment/quote/',
			'/id_desc/'
		}
	}
}