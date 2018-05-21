# 5/20/2018
#
# Berlusconi is a market which has grown steadily. Originally it had ties 
# to the the Italian darkweb scene and likely still has, but it does cater
# to an international audience.
#
# The market offers extensive details on vendors, which is ripe for analysis.
# We collect both banned vendors and their ratings, disputes the vendor has 
# been in and so forth.
#
# On Berlusconi we collect information on ratings through Ads. Ads follow
# a multilisting structure, but each ad has its own reviews. Ads are 
# therefore not noted as multilistings and every Ad can be attached to a 
# review. Becaue price is included, the shipping costs and quantity can
# also be deduced.

settings = {
    'timezone' : 'UTC',								# Timezone used on the website. 
    'endpoint' : 'http://3m2pyft7fyzjqymu.onion',	# Endpoint of the site. Hostname only 
    'prefix' : '',					# http://myhost.onion/prefix1/prefixe2/profix3/page.php
    'resources' : {									# List of availables resources. Url can be created like
        'index' 	: '/',
        'login' 	: '/?c=users&a=login'
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
        'python': {
            'username': 'python',
            'password': 'pass0000'
        }
    },
    'exclude' : { 
        'prefix' : {
        },
        'regex' :{
            'profile',
            'order',
            'logout'
        }
    },
    'priority': {
        'product': {
            'regex': 'c=listings&a=product&code=[\w]+$',
            'value': -1
        },
        'product_tac': {
            'regex': 'c=listings&a=product&code=[\w]+&tab=2$',
            'value': -2
        },
        'product_rating': {
            'regex': 'c=listings&a=product&code=[\w]+&tab=3',
            'value': -2
        },
        'user': {
            'regex': 'c=listings&a=vendor&v_id=[\w]+$',
            'value': -3
        },
        'user_tac': {
            'regex': 'c=listings&a=vendor&v_id=[\w]+&tab=2$',
            'value': -4
        },
        'user_pgp': {
            'regex': 'c=listings&a=vendor&v_id=[\w]+&tab=3$',
            'value': -4
        },
        'user_rating': {
            'regex': 'c=listings&a=vendor&v_id=[\w]+&tab=4',
            'value': -4
        }
    }
}
