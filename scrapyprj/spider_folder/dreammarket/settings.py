# Some settings specific to a spider.
# The required settings are listed in this template file.

# Copy this file for each spider.

settings = {
	'timezone' : 'UTC',								# Timezone used on the website. 
	'endpoint' : 'http://lchudifyeqm4ldjj.onion',	# Endpoint of the site. Hostname only
	'prefix' : '',					# http://myhost.onion/prefix1/prefixe2/profix3/page.php
	'resources' : {									# List of availables resources. Url can be created like   self.make_url('MyResource1')  = http://blahblahblah.onion/prefix1/prefix2/section1/page2.php
		'index' : "/"
		},
	
	'logins' : {				# Login information. They will be selected in a round robin fashioned when multiple spider is launched at once.
		'malleybono': {			# The selected login information is avalaible through  self.login
			'username' : 'malleybono',
			'password' : 'pass0000'
		},
		'lkdsegksjhgdfb': {		
			'username' : 'lkdsegksjhgdfb',
			'password' : 'pqowieuryt'
		},
		'examplescritic': {		
			'username' : 'examplescritic',
			'password' : 'pqowieuryt'
		},
		'isaacrichard': {		
			'username' : 'isaacrichard',
			'password' : 'pqowieuryt'
		},
		'laidminimize': {		
			'username' : 'laidminimize',
			'password' : 'pqowieuryt'
		},
		'webglhip': {		
			'username' : 'webglhip',
			'password' : 'pqowieuryt'
		},
		'methaneoutlying': {		
			'username' : 'methaneoutlying',
			'password' : 'pqowieuryt'
		},
		'absolutecrib': {		
			'username' : 'absolutecrib',
			'password' : 'pqowieuryt'
		},
		'logisticvenerated': {		
			'username' : 'logisticvenerated',
			'password' : 'pqowieuryt'
		},
		'variantisapi': {		
			'username' : 'variantisapi',
			'password' : 'pqowieuryt'
		},
		'bumphamilton': {		
			'username' : 'bumphamilton',
			'password' : 'pqowieuryt'
		},
		'rawfishbipedal': {		
			'username' : 'rawfishbipedal',
			'password' : 'pqowieuryt'
		},
		'metalmalboro': {		
			'username' : 'metalmalboro',
			'password' : 'pqowieuryt'
		},
		'maggotfrantic': {		
			'username' : 'maggotfrantic',
			'password' : 'pqowieuryt'
		},
		'vectorchampion': {		
			'username' : 'vectorchampion',
			'password' : 'pqowieuryt'
		},
		'evolvedbegging': {		
			'username' : 'evolvedbegging',
			'password' : 'pqowieuryt'
		},
		'worshipterrestrial': {		
			'username' : 'worshipterrestrial',
			'password' : 'pqowieuryt'
		},
		'heelperseus': {		
			'username' : 'heelperseus',
			'password' : 'pqowieuryt'
		},
		'bibspanel': {		
			'username' : 'bibspanel',
			'password' : 'pqowieuryt'
		},
		'unctiongodwottery': {		
			'username' : 'unctiongodwottery',
			'password' : 'pqowieuryt'
		}
	}
}