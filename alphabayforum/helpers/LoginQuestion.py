import re
import parser

from torforum_crawler.database.orm.models import CaptchaQuestion
from torforum_crawler.thirdparties import parse_number

def answer(q, qhash=None):
	val = "yes"
	q=q.strip()

	if qhash:
		pass #Check database for hashes

 	if q.startswith('Solve'):      		# Solve 5 + (2 x 3)
		r = re.compile("Solve (.*)")
		q = q.replace('x', '*')
 		m = r.match(q)	# Math question of type "Solve 5 + (2 x 3)"
	 	if m:
	 		code = parser.expr(m.group(1)).compile()	# Code injection safe eval.
	 		val = eval(code)

	elif q.startswith('What is'):		#What is fifty-five [plus] five?
	 	r = re.compile('What is (.*)')
	 	m = r.match(q)
	 	if m:
	 		expression = m.group(1) # fifty-five + five
	 		numbers = re.split('\[plus\]|\[minus\]|\[multiplied by\]|\[divided by\]', expression)
	 		numbers = map(str.strip, numbers)
	 		for number in numbers:
	 			expression = expression.replace(number, str(parse_number.parse_number(number)));
				
				expression = expression.replace('[plus]', '+')
				expression = expression.replace('[minus]', '-')
				expression = expression.replace('[multiplied by]', '*')
				expression = expression.replace('[divided by]', '/')

	 		code = parser.expr(expression).compile()	# Code injection safe eval.
	 		val = eval(code)

 	return val

def lookup(spider, qhash):
	return CaptchaQuestion.create_or_get(spider=spider, hash=qhash)[0]
	
#What is fifty-five [plus] five?