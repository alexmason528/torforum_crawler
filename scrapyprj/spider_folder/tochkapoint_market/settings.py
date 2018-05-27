# Tochka/Point is one of the longest-running DNMs. The market has been around since ~2014,
# and has remained stable. The market is an outlier, having displayed a number of peculiar
# behaviors including launching an ICO, open-sourcing their code and explicitly discussing
# political philosophy.
#
# The spider is able to spider the page well using default structure. Prioritized requests,
# and recursive crawling is used. Be mindful of the category exclude regexes in the exlcude
# list. These keep us from following thousands of category searches. 
#
# Tochka is built different to the average DNM. Ads follow a multilisting structure,
# but since reviews are attached to the main ID, the sublisting ID's are not usable.
# These are however collected under the field shipping_options including shipping methods
# price, quantity, etc.
#
# Tochka has publicly available buyer profiles. These are saved next to vendors in the DB
# with the is_buyer field set to True. You will also find buyers' profile texts, join_date,
# and, country and last_active there. We have full usernames on buyers, so all this metadata
# can be combined with transactions.
#
# Also, make note that Tochka has severa tidbits of interesting information on vendors. 
# "Warnings" made by users, their dialogue with staff on verification and more is all saved.


settings = {
    'timezone': 'UTC',                             # Timezone used on the website.
    'endpoint': 'http://pointgg344ghbo2s.onion/',  # Endpoint of the site. Hostname only
    'prefix': '',                                  # http://myhost.onion/prefix1/prefixe2/profix3/page.php
    'resources': {                                 # List of availables resources. Url can be created like   self.make_url('MyResource1')  = http://blahblahblah.onion/prefix1/prefix2/section1/page2.php
        'index': '/marketplace',
        'login': '/auth/login',
        },
    'logins': {                     # Login information. They will be selected in a round robin fashioned when multiple spider is launched at once.
        'poseidonsfeet': {          # The selected login information is avalaible through  self.login
            'username': 'poseidonsfeet',
            'password': 'pass0000'
        },
        'akwardpenguin': {
            'username': 'akwardpenguin',
            'password': 'pass0000'
        },
        'bigpete': {
            'username': 'bigpete',
            'password': 'pass0000'
        },
        'sadkolibri': {
            'username': 'sadkolibri',
            'password': 'pass0000'
        },
        'angrybeaver': {
            'username': 'angrybeaver',
            'password': 'pass0000'
        },
        'tomboy1': {
            'username': 'tomboy1',
            'password': 'pass0000'
        },
        'smallobjecta': {
            'username': 'smallobjecta',
            'password': 'pass0000'
        },
        'egodeathcircle': {
            'username': 'egodeathcircle',
            'password': 'pass0000'
        },
        'oedipuscomplex': {
            'username': 'oedipuscomplex',
            'password': 'pass0000'
        },
        'bigothers': {
            'username': 'bigothers',
            'password': 'pass0000'
        }
    },
    'exclude': {
        'prefix': {
            '/messages',
            '/support',
            '/help',
            '/profile',
            '/account',
            '/referrals',
            '/settings',
            '/wallet',
            '/auth/logout',
            '/auth/login',
            '/auth/register',
            '/shoutbox',
            '/payments',
            '/feed'
        },
        'regex': {
            '&sortby=date',
            '&sortby=rating',
            '&sortby=price',
            '&shipping-to=[a-zA-Z]',
            r'all%3cnil%3e'
        }
    },
    'priority': {
        'listing': {
            'regex': '/item/',
            'value': -2
        },
        'vendor': {
            'regex': '/user/',
            'value': -1
        },
    }
}
