from peewee import *
from pytz import timezone
import os, time
import re
from datetime import datetime
# Placeholder for the database connection. 
# Read peewee's documentation for more details.
proxy = Proxy()	


def set_timezone(tz=None):
	if not tz:
		tz = os.environ['TZ']
	offset = datetime.now(timezone(tz)).strftime("%z")
	m = re.match('^([+-]?)(\d{2})(\d{2})$', offset )
	if m:
		offset = "%s%s:%s" % (m.group(1), m.group(2), m.group(3))
		proxy.execute_sql('set time_zone ="%s"' % offset) 
	else:
		raise ValueError("Cannot find the timezone offset in %s" , offset)

def init(dbsettings):
	db = MySQLDatabase(dbsettings['dbname'],host=dbsettings['host'], user=dbsettings['user'], password=dbsettings['password'], charset=dbsettings['charset'])
	proxy.initialize(db);
	if 'timezone' in dbsettings:
		set_timezone(dbsettings['timezone'])

