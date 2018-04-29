settings = {
    'timezone': 'UTC',                             # Timezone used on the website.
    'endpoint': 'http://forum.cgmcoopwhempo6a5.onion/',    # Endpoint of the site. Hostname only
    'endpoint1': 'http://cgmcoopwhempo6a5.onion/',
    'prefix': '',                  # http://myhost.onion/prefix1/prefixe2/profix3/page.php
    'resources': {                                 # List of availables resources. Url can be created like   self.make_url('MyResource1')  = http://blahblahblah.onion/prefix1/prefix2/section1/page2.php
        'index': "/",
        'dologin': '/login.php'
        },
    'logins': {          # Login information. They will be selected in a round robin fashioned when multiple spider is launched at once.
        'malleybono': {  # The selected login information is avalaible through  self.login
            'username': 'malleybono',
            'password': 'pass0000'
        },
        'atomscurl': {
            'username': 'atomscurl',
            'password': 'pass0000'
        },
        'marlboroman': {
            'username': 'marlboroman',
            'password': 'pass0000'
        },
        'egotisticgiraffe': {
            'username': 'egotisticgiraffe',
            'password': 'pass0000'
        }
    },
    # Exclude lists for URIs that we shouldn't visit
    'exclude': {
        'prefix': {  # Prefix exclude like '/account/' everything like '/account/logout' or '/account/settings' will be excluded
            # '/login',
            '/account/',
            '/forum/create',
            '/forum/vote',
            '/forum/report_comment/',
            '/forum/subscribe/',
            '/forum/toggle_subscription/',
            '/forum/reply_blog_post_comment',
            '/forum/quote_blog_post_comment',
            '/forum/comment_blog_post',
            '/faq/',
            '/recency/',
            '/i/',
            '/name_asc/',
            '/comment/',
            '/blog/',
            '/post/'
        },
        'regex': {  # Regex prefixes, ran against the url part that comes after '.onion/'
            '/discussion/\d+/comment/reply/',
            '/discussion/\d+/comment/quote/',
            '/discussions/all/recency',
            '/id_desc/',
            '/order/',
            '/listings/',
            '/p/',
            '/\?do',
            '\[ToggleUserSubscription\]'
        }
    }
}