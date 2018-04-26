settings = {
    'timezone' : 'UTC',
    'endpoint' : 'http://forumsyidmkhmqhq.onion',
    'prefix' : '',
    'resources' : {
        'loginpage' : 'ucp.php?mode=login',
        'index' : 'index.php'
    },

    'logins' : {
        'vivarossa1': {
            'username' : 'vivarossa1',
            'password' : 'pass0000'
        },
        'poseidonsfeet': {
            'username': 'poseidonsfeet',
            'password': 'pass0000'
        },
        'floppy' : {
            'username': 'floppy',
            'password': 'pass0000'
        },
        'giraffe' : {
            'username': 'giraffe',
            'password': 'pass0000'
        },
        'radiator' : {
            'username': 'radiator',
            'password': 'pass0000'
        }
    },
    'exclude' : {
        'prefix' : {
            # Prefix with '#' will be excluded
            '#',
            'http://',
            '/report',
            '/posting.php'
        },
        'regex' : { # Regex prefixes, ran against the url part that comes after '.onion/'
            r'search\.php',
            r'ucp\.php',
            'mailto:',
            'mode=quote'
        }
    }
}
