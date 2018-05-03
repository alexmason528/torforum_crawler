settings = {
	'timezone' : 'GMT',
	'endpoint' : 'http://avengersdutyk3xf.onion',
	'prefix' : '',
	'resources' : {
		'loginpage' : 'index.php?action=login',
		'index' : 'index.php'
		},
	
	'logins' : {
		'vivarossa1': {
			'username' : 'vivarossa1',
			'password' : 'pass0000'
		},
		'vivarossa2': {
			'username' : 'vivarossa2',
			'password' : 'pass0000',
		},
		'vivarossa3': {
			'username' : 'vivarossa3',
			'password' : 'pass0000',
		},
		'akwardpenguin': {
			'username': 'akwardpenguin',
			'password': 'pass0000'
		},
		'hungryman': {
			'username': 'hungryman',
			'password': 'pass0000'
		}		
	},
	
	'exclude' : {
		'prefix' : { # Prefix exclude like '/account/' everything like '/account/logout' or '/account/settings' will be excluded
			'/#',
		},
		'regex' : { # Regex prefixes, ran against the url part that comes after '.onion/'
			'/#',
			'/index\.php\?action=profile;area',
			'/index\.php\?action=unread',
			'/index\.php\?action=unreadreplies',
			'/index\.php\?action=help',
			'/index\.php\?action=search',
			'/index\.php\?action=pm',
			'/index\.php\?action=mlist',
			'/index\.php\?action=logout',
			'/index\.php\?action=collapse',
			'/index\.php\?action=markasread',
			'/index\.php\?action=stats',
			'/index\.php\?action=recent',
			'/index\.php\?action=who',
			'/index\.php\?action=\.xml',
			'/index\.php\?wap2',
			'/index\.php\?action=post;',
			'/index\.php\?action=notify',
			'/index\.php\?action=reporttm',
			'/index\.php\?action=emailuser',
			'/index\.php\?topic=\d+\.msg',
			'/javascript',
			'/index\.php\?action=reminder',
			'/index\.php\?action=buddy',
			'/index\.php\?board=\d+\.\d+\;sort',
			'/index\.php\?topic=\d+\.\d+\;prev_next=next',
			'/index\.php\?topic=\d+\.\d+\;prev_next=prev',
			'/index\.php\?action=login',
			'/mailto',
			'action=printpage',
			'action=profile;area=index;sa=settings',
			'togglebar$',
			'action=profile;area=account;u=31284',
			'action=profile;area=forumprofile',
			'action=profile;area=theme',
			'action=profile;area=notification',
			'action=profile;area=pmprefs',
			'action=profile;area=lists',
			';area=summary$'
		}
	}
}