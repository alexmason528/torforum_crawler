# Some settings specific to a spider.
# The required settings are listed in this template file.

# Copy this file for each spider.

settings = {
	'timezone' : 'UTC',								# Timezone used on the website. 
	'endpoint' : 'http://libbyxh6som2twgp.onion',	# Endpoint of the site. Hostname only
	'prefix' : '',					# http://myhost.onion/prefix1/prefixe2/profix3/page.php
	'resources' : {									# List of availables resources. Url can be created like   self.make_url('MyResource1')  = http://blahblahblah.onion/prefix1/prefix2/section1/page2.php
		'login' 	: "/login",
		'ads_list' 	: "/advanced-search?index=&category=&term=&ships-from=&unit=&unit-value=&order-by=&payment-option=&active-vendors=&price-from=&price-to="
		},
	
	'logins' : {				# Login information. They will be selected in a round robin fashioned when multiple spider is launched at once.
		'vivarossa1': {			# The selected login information is avalaible through  self.login
			'username' : 'vivarossa1',
			'password' : 'pass0000'
		}
	}
}