from peewee import *

# Placeholder for the database connection. 
# Read peewee's documentation for more details.
proxy = Proxy()	


def set_timezone(timezone):
	proxy.execute_sql('set time_zone ="%s"' % timezone) 

def init(dbsettings):
	db = MySQLDatabase(dbsettings['dbname'],host=dbsettings['host'], user=dbsettings['user'], password=dbsettings['password'], charset=dbsettings['charset'])
	proxy.initialize(db);
	if 'timezone' in dbsettings:
		set_timezone(dbsettings['timezone'])

