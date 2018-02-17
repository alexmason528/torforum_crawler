# Some settings specific to a spider.
# The required settings are listed in this template file.

# Copy this file for each spider.

settings = {
	'timezone' : 'UTC',								# Timezone used on the website. 
	#'endpoint' : 'http://uffti3lhacanefgy.onion', # Using a mirror. URL below is main.
	'endpoint' : 'http://kzda2greas4thbbp.onion',	# Endpoint of the site. Hostname only
	'prefix' : '',					# http://myhost.onion/prefix1/prefixe2/profix3/page.php
	'resources' : {									# List of availables resources. Url can be created like   self.make_url('MyResource1')  = http://blahblahblah.onion/prefix1/prefix2/section1/page2.php
		'index' : "/"
		},
	
	'logins' : {				# Login information. They will be selected in a round robin fashioned when multiple spider is launched at once.
		'malleybono': {			# The selected login information is avalaible through  self.login
			'username' : 'malleybono',
			'password' : 'pass0000'
		},
		'atomscurl': {		
			'username' : 'atomscurl',
			'password' : 'pass0000'
		},
		'ocelotcylinders': {		
			'username' : 'ocelotcylinders',
			'password' : 'pass0000'
		},
		'stirringtoddlers': {		
			'username' : 'stirringtoddlers',
			'password' : 'pass0000'
		},
		'baguetterabbitsfoot': {		
			'username' : 'baguetterabbitsfoot',
			'password' : 'pass0000'
		},
		'shoddyalmond': {		
			'username' : 'shoddyalmond',
			'password' : 'pass0000'
		},
		'methaneoutlying': {		
			'username' : 'methaneoutlying',
			'password' : 'pqowieuryt'
		},
		'mimicrycomposed': {		
			'username' : 'mimicrycomposed',
			'password' : 'pass0000'
		},
		'gratifiedmixcloud': {		
			'username' : 'gratifiedmixcloud',
			'password' : 'pass0000'
		},
		'carillonaffine': {		
			'username' : 'carillonaffine',
			'password' : 'pass0000'
		},
		'bumphamilton': {		
			'username' : 'bumphamilton',
			'password' : 'pqowieuryt'
		},
		'untriedmineral': {		
			'username' : 'untriedmineral',
			'password' : 'pass0000'
		},
		'metalmalboro': {		
			'username' : 'metalmalboro',
			'password' : 'pqowieuryt'
		},
		'wholesalebah': {		
			'username' : 'wholesalebah',
			'password' : 'pass0000'
		},
		'annumgadwall': {		
			'username' : 'annumgadwall',
			'password' : 'pass0000'
		},
		'italybowline': {		
			'username' : 'italybowline',
			'password' : 'pass0000'
		},
		'measureretrieve': {		
			'username' : 'measureretrieve',
			'password' : 'pass0000'
		},
		'heelperseus': {		
			'username' : 'heelperseus',
			'password' : 'pqowieuryt'
		},
		'appearcrossed': {		
			'username' : 'appearcrossed',
			'password' : 'pass0000'
		},
		'archivestwinkling': {		
			'username' : 'archivestwinkling',
			'password' : 'pass0000'
		},
		'analyticcavity': {		
			'username' : 'analyticcavity',
			'password' : 'pass0000'
		},
		'huhrocket': {		
			'username' : 'huhrocket',
			'password' : 'pass0000'
		},
		'newkiedrhyolite': {		
			'username' : 'newkiedrhyolite',
			'password' : 'pass0000'
		}
	}
}




