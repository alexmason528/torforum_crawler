settings = {
    'timezone' : 'UTC',								# Timezone used on the website. 
    'endpoint' : 'http://fdwmarkvokb5i7wh.onion',	# Endpoint of the site. Hostname only 
    'prefix' : '',					# http://myhost.onion/prefix1/prefixe2/profix3/page.php
    'resources' : {									# List of availables resources. Url can be created like
        'index' 	: '/',
        'login' 	: '/login'
    },
    'logins' : {				# Login information. They will be selected in a round robin fashioned when multiple spider is launched at once.
        'vivarossa1': {			# The selected login information is avalaible through  self.login
            'username' : 'vivarossa1',
            'password' : 'pass0000'
        },
        'discontent': {
            'username': 'discontent',
            'password': 'pass0000'
        },
        'mediocresquirrel': {
            'username': 'mediocresquirrel',
            'password': 'pass0000'
        },
        'jeanne97': {
            'username': 'jeanne97',
            'password': 'pass0000'
        },
        'pypypypy': {
            'username': 'pypypypy',
            'password': 'pass0000'
        }
    },
    'exclude' : { 
        'prefix' : {
            '/order_by/',
            '/logout/',
            '/scam_report/',
            '/account/modify/',
            '/account/verify/',
            '/password_change/',
            '/feedbacks/add_feedback/',
            '/feedbacks/add_feedbackcomment/',
            '#'
        },
        'regex' :{
            '\.jpg$',
            '\.JPG$',
            '\.jpeg$',
            '\.JPEG$'
            '/messages/write/',
            '\.png$',
            '\.PNG$',
            '\.bmp$',
            '\.BMP$',
            '\.gif$',
            '\/.pdf'
        }
    },
    'priority': {
        'product': {
            'regex': '/product/[\w-]+/$',
            'value': -1
        },
        'user': {
            'regex': '/account/[\w-]+/$',
            'value': -2
        },
        'feedback': {
            'regex': '/feedbacks/feedback_list/[\w-]+/',
            'value': -3
        }
    }
}