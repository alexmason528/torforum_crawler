settings = {
	'timezone' : 'UTC',
	'endpoint' : 'http://kbyz2vu3fnv2di7l.onion',
	'prefix' : '',
	'resources' : {
		'loginpage' : 'member.php',
		'index' : 'index.php',
		},
	
	'logins' : {
		'malleybono': {
			'username' : 'malleybono',
			'password' : 'Hsdkhsd@432432'
		},
		'alexmason': {
			'username': 'alexmason',
			'password': 'Alexmason528'
		}
	},
	'exclude' : {
		'prefix' : { # Prefix exclude like '/account/' everything like '/account/logout' or '/account/settings' will be excluded
		},
		'regex' : { # Regex prefixes, ran against the url part that comes after '.onion/'
			'action=',
			'\?report=',
			'misc\.php\?email=',
			'search\.php',
			'register\.php',
			'post\.php',
			'#p[0-9]{1,5}',
			'mailto:'
		}
	}
}