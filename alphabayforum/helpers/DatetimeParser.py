from dateutil.parser import parse as parse  
from datetime import datetime, timedelta
import re
import calendar

def tryparse(datestr):
	datestr = datestr.lower()
	
	if datestr == "some minutes ago":
		return datetime.now()
	elif datestr.startswith(('yesterday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday')):
		m = re.match('(\w+) at (.+)', datestr)
		if m :
			day = m.group(1)
			time = m.group(2)

			if day == 'yesterday':
				day = calendar.day_name[(datetime.now().weekday()+6 )% 7];

			date = parse(day + " " + time)
			if date > datetime.now():
				date = date - timedelta(days=7)

			return date
		else:
			return None
	else:
		return parse(datestr)
