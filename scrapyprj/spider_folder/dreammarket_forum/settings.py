# Notes:
# The admin SpeedStepper deletes the time and date of his posts. To get them, 
# we therefore take the time of the proceding or preceding posts, and set the 
# time of the post 1 minute before/after. When a time cannot be found (SS is
# the only poster) a warning is dropped.



settings = {
	'timezone' : 'UTC',
	'endpoint' : 'http://tmskhzavkycdupbr.onion',
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
		'patatepoil': {
		 	'username' : 'patatepoil',
		 	'password' : 'pqowieuryt'
		},
		'moustache': {
		 	'username' : 'moustache',
		 	'password' : 'moustache'
		},
		'suspiciouspanda': {
			'username' : 'suspiciouspanda',
			'password' : 'pass0000'
		},
		 'chillcobra': {
		 	'username' : 'chillcobra',
		 	'password' : 'pass0000'
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
	},
    'priority': {
        'message': {
            'regex': 'viewtopic',
            'value': -3
        },
        'user': {
            'regex': 'profile',
            'value': -2
        },
        'threadlisting': {
            'regex': 'viewforum',
            'value': -1
        }		
	}
}