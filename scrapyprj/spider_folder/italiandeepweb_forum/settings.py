settings = {
	'timezone' : 'GMT',
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
		'negatron': {
			'username': 'negatron',
			'password': 'Pass0000'
		},
		'jacksmith': {
			'username': 'jacksmith',
			'password': 'Pass0000'
		},
		'cvvsfortheworld': {
			'username': 'cvvsfortheworld',
			'password': 'Pass0000'
		},
		'overflow': {
			'username': 'overflow',
			'password': 'Pass0000'
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