settings = {
	'timezone' : 'UTC',
	'endpoint' : 'http://fdpogivefk34xkbd.onion',
	'prefix' : '',
	'resources' : {
		'loginpage' : 'login.php',
		'index' : 'index.php'
		},
	
	'logins' : {
		'vivarossa1': {
			'username' : 'vivarossa1',
			'password' : 'pass0000'
		},
		'eagleeye': {
			'username' : 'eagleeye',
			'password' : 'pass0000'
		},
		'ocelotcylinders': {
			'username' : 'ocelotcylinders',
			'password' : 'pass0000'
		},
		'atomscurl': {
			'username': 'atomscurl',
			'password': 'pass0000'
		},
		'poseidonsfeet': {
			'username': 'poseidonsfeet',
			'password': 'pass0000'
		}
	},
	'exclude' : {
		'prefix' : { # Prefix exclude like '/account/' everything like '/account/logout' or '/account/settings' will be excluded
		},
		'regex' : { # Regex prefixes, ran against the url part that comes after '.onion/'
			'action=',
			'\?report=',
			'misc\.php',
			'search\.php',
			'register\.php',
			'post\.php',
			'profile\.php',
			'userlist\.php',
			'#p[0-9]{1,5}',
			'mailto:',
			'luhn2.php',
			'/wiki',
		}
	}
}