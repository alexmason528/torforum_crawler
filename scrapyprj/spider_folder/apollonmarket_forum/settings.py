settings = {
    'timezone': 'UTC',
    'endpoint': 'http://apollionmy7q52qc.onion',
    'prefix': '',
    'resources': {
        'loginpage': '/login.php',
        'dologin': '/login.php?action=in',
        'index': '/index.php'
        },

    'logins': {
        'poseidonsfeet': {
            'username': 'poseidonsfeet',
            'password': 'pass0000',
            'email': 'InuftqOWoZaj@tmg.lsd'
        },
        'akwardpenguin': {
            'username': 'akwardpenguin',
            'password': 'pass0000',
            'email': 'IacAvkVKPnKJ@tmg.lsd'
        },
        # 'vivarossa1': {
        #     'username': 'vivarossa1',
        #     'password': 'pass0000'
        # }
    },
    'exclude': {
        'prefix': {  # Prefix exclude like '/account/' everything like '/account/logout' or '/account/settings' will be excluded
        },
        'regex': {   # Regex prefixes, ran against the url part that comes after '.onion/'
            'action=',
            'misc\.php\?',
            'search\.php',
            'register\.php',
            'extern\.php',
            'post\.php',
            'help\.php',
            '#p[0-9]{1,5}',
            'mailto:',
            'javascript:'
        }
    }
}
