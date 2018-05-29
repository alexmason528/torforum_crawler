# Rapture Market is relatively new. It is predominantly used by British vendors
# and rumor has it is connected to British vendors. Rumor further stipulates 
# that the codebase is similar to that on the now closed TradeRoute market.
# On Raputure we collect above average quality data in the form of Sellers, 
# Products and Ratings.
#
# Like TradeRoute, Rapture uses a multilisting system, which is also similar to
# that used by CGMC. In this system a listing can be a MULTILISTING. Multilistings
# will have sublistings which are individual listings with quantities and prices.
# We therefore do not collect ads from the MULTILISTING page. However, from
# that page we generate a request for each of the sublistings, which we collect.
#
# On reviewing the product feedback page for a multilisting, it cannot be 
# distinguished whether a review is for which MULTILISTING_SUBLISTING. However, 
# in the vendor's feedback page this information is available as each review is 
# connected to a MULTILISTING_SUBLISTING. Similarly, for the MULTILISTING_SUBLISTING
# pages we can also connect the Ad-ID to to the feedback on these.
#
# To collect ProductRatings, we fetch them from the ad page for the sublisting.
# UserRatings are collected from the vendor's profile page. These
# are collected as UserRatings but include Ad ID's. The reason we use User and
# not Product Rating items is that some reviews will refer to unavaiable items.
# Because of a foreign key constraint we cannot yield ProductRatings for ads we
# have enever colected, so we need to collect them as UserRatings.
#
# For analysis, it is recommended to use the reviews from the seller pages,
# since these are both tied to sublistings, and there are more (since they don't
# require an ad to be live).
#
# CAPTCHA:
# The Rapture CAPTCHA does not specify it, but needs to have 5 of 6 characters
# submitted. A custom middleware simply strips the first character.
#
# 302's.
# We use custom 302-handling on Rapture. Sometimes we will see links to items
# that are no longer for sale in the UserRatings. These are followed, and will
# yield quite a few 302's by the end of the crawl when the low-priority user
# pages are scraped.



settings = {
    'timezone': 'UTC',                             # Timezone used on the website.
    'endpoint': 'http://zsionvz2kfzttpv3.onion/',  # Endpoint of the site. Hostname only
    'prefix': '',                                  # http://myhost.onion/prefix1/prefixe2/profix3/page.php
    'resources': {                                 # List of availables resources. Url can be created like   self.make_url('MyResource1')  = http://blahblahblah.onion/prefix1/prefix2/section1/page2.php
        'index': '/',
        'login': '/login.php',
        },
    'logins': {                     # Login information. They will be selected in a round robin fashioned when multiple spider is launched at once.
        'poseidonsfeet': {          # The selected login information is avalaible through  self.login
            'username': 'poseidonsfeet',
            'password': 'pass0000',
            'pin': 'pin0000'
        },
        'akwardpenguin': {
            'username': 'akwardpenguin',
            'password': 'pass0000',
            'pin': 'pin0000'
        },
        'bigpete': {
            'username': 'bigpete',
            'password': 'pass0000',
            'pin': 'pin0000'
        },
        'sadkolibri': {
            'username': 'sadkolibri',
            'password': 'pass0000',
            'pin': 'pin0000'
        },
        'angrybeaver': {
            'username': 'angrybeaver',
            'password': 'pass0000',
            'pin': 'pin0000'
        }
    },
    'exclude': {
        'prefix': {
            '/?logout',
            '/?page=account',
            '/?page=notifications',
            '/?page=messages',
            '/?page=orders',
            '/?page=support',
            '/?page=faq',
            '/?page=newticket',
            '/?page=referrals',
            '/?page=resetpin',
            '/?page=depositaddresses',
            '/register.php',
            '/reset.php'
        },
        'regex': {
            '&unfavorite&',
            '&favorite&',
            '&downvote=',
            '&upvote=',            
            'page=profile&user=akwardpenguin',
            'page=profile&user=bigpete',
            'page=profile&user=sadkolibri',
            'page=profile&user=angrybeaver',
            'page=profile&user=poseidonsfeet',
            '\?page=report&'
        }
    },
    'priority': {
        'listing': {
            'regex': 'page=listing&lid=',
            'value': -3
        },
        'vendor': {
            'regex': 'page=profile&user=',
            'value': -4
        },
    }
}
