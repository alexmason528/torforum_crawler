# Some settings specific to a spider.
# The required settings are listed in this template file.

# Copy this file for each spider.

settings = {
	'timezone' : 'UTC',							# Timezone used on the website. 
	'endpoint' : 'http://blahblahblah.onion',	# Endpoint of the site. Hostname only
	'prefix' : 'prefix1/prefix2',				# http://myhost.onion/prefix1/prefixe2/profix3/page.php
	'resources' : {								# List of availables resources. Url can be created like   self.make_url('MyResource1')  = http://blahblahblah.onion/prefix1/prefix2/section1/page2.php
		'MyResource1' : "section1/page2.php",
		'MyResource2' : "section2/page4.php"
		},
	
	'logins' : {				# Login information. They will be selected in a round robin fashioned when multiple spider is launched at once.
		'MyUser1': {			# The selected login information is avalaible through  self.login
			'username' : 'abcdef',
			'password' : 'qwerty',
			'SomeField1' : 'SomeValue'
		},
		'MyUser2': {
			'username' : '123456789',
			'password' : 'kitten123',
			'SomeField2' : 'SomeValue2'
		}

	}
}