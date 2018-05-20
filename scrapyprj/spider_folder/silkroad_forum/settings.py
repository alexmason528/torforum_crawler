settings = {
	'timezone' : 'UTC',
	'endpoint' : 'http://satri4bb5r56y253.onion',
	'prefix' : '',
	'resources' : {
		'loginpage' : 'ucp.php?mode=login',
		'index' : 'index.php'
		},
	
	'logins' : {
		'vivarossa1': {
			'username' : 'vivarossa1',
			'password' : 'Pass0000!'
		},
		'happyhippo': {
			'username' : 'happyhippo',
			'password' : 'Pass0000!'
		},
		'angrypenguin': {
			'username' : 'angrypenguin',
			'password' : 'Pass0000!'
		},
		'dropkickbeaver': {
			'username' : 'dropkickbeaver',
			'password' : 'Pass0000!'
		},
		'athenashammer': {
			'username' : 'athenashammer',
			'password' : 'Pass0000!'
		}
	},

	'exclude' : {
		'prefix' : { # Prefix exclude like '/account/' everything like '/account/logout' or '/account/settings' will be excluded
			'silkroad7rn2puhj.onion/',
		},
		'regex' : { # Regex prefixes, ran against the url part that comes after '.onion/'
			'ucp\.php',
			'app\.php',
			'posting\.php',
			'bitcoin\:',
			'search\.php',
			'uid=',
			'\#top',
			'mode=team',
			'hash=',
			'first_char=',
			'view=print',
			'mode=searchuser',
			'view=unread',
			'&sid=',
			'&recent_topics',
			'/\./\.\./',
			'file\.php'
		}
	},
    'priority' : {
        'user': {
            'regex': 'viewprofile',
            'value': -1
        },
        'threadlisting': {
            'regex': 'viewforum',
            'value': -2
        },
        'messages': {
            'regex': 'viewtopic',
            'value': -3
        }
    }
}