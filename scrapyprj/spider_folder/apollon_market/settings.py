# Apollon is likely a merger between RSClub and IDC. Both markets went offline,
# but RSClub began redirecting to Apollon which had the Favicon of IDC. In 
# addition, the layout and structure are identical. The market is predominantly
# used by an Italian base but is slowly branching out internationally.
#
# On the market we collect product ratings from listing pages. They are also 
# available on vendor pages, but they are identical. Note, that each review
# has an associated price. Manual inspection suggests that these prices are NOT
# representative of quantity or shipping expenses, but only reflect the price of
# 1 item. 
#
# On seller pages, Apollon offers quite a lot of information which may be of
# interest. Note, that the number of disputes the vendor has engaged in is 
# available, two levels badges, FE-privileges, and the number of order made
# by the seller. 


settings = {
    'timezone': 'UTC',                             # Timezone used on the website.
    'endpoint': 'http://apollionih4ocqyd.onion/',  # Endpoint of the site. Hostname only
    'prefix': '',                                  # http://myhost.onion/prefix1/prefixe2/profix3/page.php
    'resources': {                                 # List of availables resources. Url can be created like   self.make_url('MyResource1')  = http://blahblahblah.onion/prefix1/prefix2/section1/page2.php
        'index': '/',
        'login': '/login.php',
        },
    'logins': {                     # Login information. They will be selected in a round robin fashioned when multiple spider is launched at once.
        'poseidonsfeet': {          # The selected login information is avalaible through  self.login
            'username': 'poseidonsfeet',
            'password': 'pass0000',
            'pin': '000000'
        },
        'akwardpenguin': {
            'username': 'akwardpenguin',
            'password': 'pass0000',
            'pin': '000000'
        },
        'bigpete': {
            'username': 'bigpete',
            'password': 'pass0000',
            'pin': '000000'
        },
        'sadkolibri': {
            'username': 'sadkolibri',
            'password': 'pass0000',
            'pin': '000000'
        },
        'vivarossa1': {
            'username': 'vivarossa1',
            'password': 'pass0000'
        }
    },
    'exclude': {
        'prefix': {
            '/logout.php',
            'login.php',
            '/imsg.php',
            '/orders.php',
            '/seller.php',
            '/profile.php',
            '/autoshop.php',
            '/affiliate.php',
            '/deposit.php',
            '/myfavourites.php',
            '/myblacklist.php',
            '/support.php',
            '/forgotpin.php',
            '/smsg.php',
            '/home.php?cid=0&csid=0'
        },
        'regex': {
            '&report=',
            '&imgid=',
            '&fvusr=',
            '&fvlst='
        }
    },
    'priority': {
        # 'listing': {
        #     'regex': 'listing\.php\?ls_id',
        #     'value': -1
        # },
        # 'vendor': {
        #     'regex': 'user\.php\?u_id',
        #     'value': -2
        # },
    }
}
