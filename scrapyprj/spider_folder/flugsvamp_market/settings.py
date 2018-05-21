# Flugsvamp 2.0 is the second incarnation of the Flugsvamp brand. Allegedly, the first
# incarnation disappeared around Operation Onymous but no seizures or the like happened
# around then. Rather, the site seems to have been relaunched. Flugsvamp has operated
# for more than 1-2 years at the date of writing the spider. 
#
# The market is explicitly designed and limited for a Swedish audience. There have been
# talks of branching out to Norway, but presently nothing has happened. 
#
# The market offers sparser data than usually. Reviews are unavailable, and so are vendor
# profiles. The latter we construct using informaiton on product pages. Information on 
# sales can be learned from vendor and product propvals (e.g. feedbacks rceived).



settings = {
	'timezone' : 'UTC',							
	'endpoint' : 'http://flugsvamp72rajmk.onion/',
	'prefix' : '',					
	'resources' : {									
		'index' : "/",
		'loginpage' : "/"
		},
	
	'logins' : {				
		'vivarossa1': {			
			'username' : 'vivarossa1',
			'password' : 'pass0000'
		},
		'atomscurl': {		
			'username' : 'atomscurl',
			'password' : 'pass0000'
		},
		'malleybono': {		
			'username' : 'malleybono',
			'password' : 'pass0000'
		},
		'poseidonsfeet': {		
			'username' : 'poseidonsfeet',
			'password' : 'pass0000'
		},
		'ocelotcylinders': {		
			'username' : 'ocelotcylinders',
			'password' : 'pass0000'
		}
	},
	'exclude' : { 
		'prefix' : {
			'\&fav=1',
			'pgpguide=',
			'faq=',
			'sakerhet=',
			'deponering=',
			'saljare=',
			'vaxlapengar=',
			'anvklasser=',
			'msg=',
			'up=',
			'grundinfo=',
			'/images\/',
			'stealthmode=1',
			'p=.*\&',			
		},
		'regex' :{
			'/images\/',
			'\&fav=1',
			'php\?l=1',
			'php\?=1',
			'\?favs=1',
			'\?acc=1',
			'\.php\?a=',
			'php\?pgpguide=1',
			'php\?faq=1',
			'php\?sakerhet=1',
			'php\?deponering=1',
			'php\?saljare=1',
			'php\?vaxlapengar=1',
			'php\?anvklasser=1',
			'php\?msg=1',
			'php\?up=',
			'php\?grundinfo=1',
			'/images\/orginal\/',
			'php\?p=.*\&',
			'php\?pengar=1',
			'stealthmode=1',
		}
	},
	'priority': {
	}	
}
