# CGMC is a cannabis- and psychedelics only market. It offers an onsite discussion forum,
# where buyers and vendors post and comment under their own names. If further offers 
# blogging functionality. This is not processed presently, but can be recovered from 
# replays. CGMC require a waiting period of 24-48 hours before a profile can be activated.
# If you need to make new logins, get a bunch of invite codes and save them in this file
# for later use.
#
# Vendor activity on market and forum can be connected through their profiles. 
# Interestingly, some vendors cannot be recognized by their URL (/v/ versurs /u/). Be 
# aware of this for analysis.




settings = {
    'timezone': 'UTC',                             
    'endpoint': 'http://forum.cgmcoopwhempo6a5.onion/',    
    'endpoint1': 'http://cgmcoopwhempo6a5.onion/',
    'prefix': '',                  
    'resources': {                               
        'index': "/",
        'dologin': '/login.php'
        },
    'logins': {          
        'malleybono': {  
            'username': 'malleybono',
            'password': 'pass0000'
        },
        'atomscurl': {
            'username': 'atomscurl',
            'password': 'pass0000'
        },
        'haphazardly': {
            'username': 'haphazardly',
            'password': 'pass0000'
        },
        'knowableenigma': {
            'username': 'knowableenigma',
            'password': 'pass0000'
        },
        'paperclip': {
            'username': 'paperclip',
            'password': 'pass0000'
        }
    },
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
            '\[ToggleUserSubscription\]',
            '/comments/' # Comments are actually ratings. We do not need to collect them, as they are collected by the market spider.
        }
    }
}