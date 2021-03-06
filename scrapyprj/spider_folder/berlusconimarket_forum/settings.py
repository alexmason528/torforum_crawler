settings = {
    'timezone': 'GMT',
    'endpoint': 'http://lokwbo54utdfvr4r.onion/',
    'prefix': '',
    'resources': {
        'homepage': '/index.php',
        'index': '/',
        'dologin': '/member.php',
        'loginpage': '/member.php?action=login'
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
        'gambini': {
            'username': 'gambini',
            'password': 'pass0000'
        },
        'slippery': {
            'username': 'slippery',
            'password': 'pass0000'
        },
        'pawnpin': {
            'username': 'pawnpin',
            'password': 'pass0000'
        },
        'threadshower': {
            'username' : 'threadshower',
            'password' : 'pass0000'
        }
    },
    'exclude': {
        'prefix': {
            '/printthread.php',
            '/javascript',
            '/private.php',
            '/newreply.php',
            '/./',
            '/search.php',
            '/announcements.php',
            '/misc.php',
            '/reputation.php',
            '/usercp',
            '/newthread.php',
            '/online.php'
        },
        'regex': {
            'c=listings',
            'action=logout',
            'action=emailuser',
            'action=resendactivation',
            '&action=nextoldest',
            'mode=threaded',
            'mode=linear',
            '&sortby=',
            '&action=nextnewest',
            '#pid', 
            'tid=[0-9]{1,10000}&pid=', # There is no reason to go to links which refer to posts in a thread we already spider.
            '&action=lastpost'
        }
    }
}
