settings = {
    'timezone': 'GMT+1',
    'endpoint': 'http://nzlbyrcvvqtrkxiu.onion/',
    'prefix': '',
    'resources': {
        'loginpage': '/index.php',
        'dologin': '/index.php?action=login2',
        'index': '/index.php'
        },

    'logins': {
        # 'poseidonsfeet': {
        #     'username': 'poseidonsfeet',
        #     'password': 'pass0000',
        #     'email': 'InuftqOWoZaj@tmg.lsd'
        # },
        # 'akwardpenguin': {
        #     'username': 'akwardpenguin',
        #     'password': 'pass0000',
        #     'email': 'IacAvkVKPnKJ@tmg.lsd'
        # },
        'vivarossa1': {
            'username': 'vivarossa1',
            'password': 'pass0000'
        }
    },
    'exclude': {
        'prefix': {  # Prefix exclude like '/account/' everything like '/account/logout' or '/account/settings' will be excluded
        },
        'regex': {  # Regex prefixes, ran against the url part that comes after '.onion/'
            'index\.php\?action=profile',
            'index\.php\?action=search',
            'index\.php\?action=help',
            'index\.php\?action=emailuser',
            'index\.php\?action=stats',
            'index\.php\?action=recent',
            'index\.php\?action=credits',
            'index\.php\?action=replyall',
            'index\.php\?action=replynew',
            'index\.php\?action=collapse',
            'index\.php\?action=unread',
            'index\.php\?action=reporttm',
            'index\.php\?action=printpage',
            'index\.php\?action=notify',
            'index\.php\?action=post',
            'index\.php\?action=pm',
            'index\.php\?action=markasread',
            'index\.php\?action=logout',
            'index\.php\?action=helpadmin',
            'javascript\:',
            'topic=\d+\.msg\d+',
            ';sort=',
            ';prev_next=',
        }
    }
}
