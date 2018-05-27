# Olympus is a relatively new market on the scene, being launched in 2018 (By RM's estimate).
# At the time on which the spider was first deployed, the market was stil small in size, but
# had many vendors operating. There is a large discrepancy in the number of ads relative to 
# the number of reviews.
#
# On Olympus we use a recursive spider. We prioritize requests and run parsers dependent
# on the URL. We collect both Seller and Product Rating items. Obviously, thus will give
# some overlap between the two classes. For an analysis, you should not use both. The reason
# we collect both is that the former type includes the specific price paid. Do note, that the
# dates given for reviews do not look like they are precise. There are, for example, no reviews
# posted 2 weeks ad 1 days ago. Only 2 weeks ago.
#
# On May 19th it was tested whether Olympus fraudulently inflated the number of listings. This
# was done by counting the number of listings in the subcategory "Cocaine" and comparing it to
# the advertised number of listings in the category. An inflation of more than 50% was found.
# Thus, there is reason to believe the market inflates listings, which explains the discrepancy
# between observed and advertised numbers of listings.
#

settings = {
    'timezone' : 'UTC',								# Timezone used on the website. 
    'endpoint' : 'http://xc7oyzq4cz3ki7sa.onion/',	# Endpoint of the site. Hostname only 
    'prefix' : '',					# http://myhost.onion/prefix1/prefixe2/profix3/page.php
    'resources' : {									# List of availables resources. Url can be created like
        'index' 	: '/',
        'login' 	: '/signin'
    },
    'logins' : {				# Login information. They will be selected in a round robin fashioned when multiple spider is launched at once.
        'vivarossa1': {			# The selected login information is avalaible through  self.login
            'username' : 'vivarossa1',
            'password' : 'pass0000'
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
        },
        'onion': {
            'username': 'onion',
            'password': 'pass0000'
        },
        'shymouse': {
            'username': 'shymouse',
            'password': 'pass0000'
        },
        'aida32': {
            'username': 'aida32',
            'password': 'pass0000'
        },
        'findnemo': {
            'username': 'findnemo',
            'password': 'pass0000'
        },
        'slayerplay': {
            'username': 'slayerplay',
            'password': 'pass0000'
        },
        'megadeth': {
            'username': 'megadeth',
            'password': 'pass0000'
        }

    },
    'exclude' : { 
        'prefix' : {
            '/mail',
            '/faq',
            '/tickets',
            '/orders',
            '/wallet',
            '/profile/edit',
            '/profile/store',
            '/notifications',
            '/stealth'
        },
        'regex' :{
            'logout',
            '#',
            '\?sort=',
            '&sort=',
            '\.jpg$',
            '\.JPG$',
            '\.jpeg$',
            '\.JPEG$'
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
            'regex': '/listings/[\w-]+/[\w-]+$',
            'value': -2
        },
        'product_tac': {
            'regex': '/listings/[\w-]+/[\w-]+/refund_policy$',
            'value': -3
        },
        'product_rating': {
            'regex': '/listings/[\w-]+/[\w-]+/feedback$',
            'value': -3
        },
        'user': {
            'regex': '/profile/view/[\w-]+$',
            'value': -1
        }
    }
}
