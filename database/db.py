from peewee import *

# Placeholder for the database connection. 
# Read peewee's documentation for more details.
proxy = Proxy()	


def init(dbsettings):
	db = MySQLDatabase(dbsettings['dbname'],host=dbsettings['host'], user=dbsettings['user'], password=dbsettings['password'], charset=dbsettings['charset'])
	proxy.initialize(db);
