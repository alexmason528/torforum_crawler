import re
import parser

from scrapyprj.database.forums.orm.models import CaptchaQuestion
from scrapyprj.thirdparties import parse_number

def answer(q, login):
	val = "yes"
	q=q.strip()
 	
 	text_expr_regex = {
 		'+' : '[\[\(]\s*plus\s*[\]\)]',
	 	'-' : '[\[\(]\s*minus\s*[\]\)]',
	 	'*' : '[\[\(]\s*multiplied by\s*[\]\)]',
	 	'/' : '[\[\(]\s*divised by\s*[\]\)]'
	 	}

	if q.lower() == 'what is your registration token' and 'registration_token' in login:
		val = login['registration_token']
 	elif q.startswith('Solve'):      		# Solve 5 + (2 x 3)
		r = re.compile("Solve (.*)")
		q = q.replace('x', '*')
 		m = r.match(q)	# Math question of type "Solve 5 + (2 x 3)"
	 	if m:
	 		code = parser.expr(m.group(1)).compile()	# Code injection safe eval.
	 		val = eval(code)

	elif re.match('What is .*('+'|'.join(text_expr_regex.values())+').*\??', q):		#What is fifty-five [plus] five?
	 	r = re.compile('What is ([^?]*)\??')
	 	m = r.match(q)

	 	if m:
	 		expression = m.group(1) # fifty-five + five
	 		numbers = re.split('|'.join(text_expr_regex.values()), expression)
	 		for number in numbers:
	 			number = number.strip()
	 			try:
	 				newnumber = int(number)
	 			except:
	 				newnumber = parse_number.parse_number(number)

	 			expression = expression.replace(number, str(newnumber));
				
				for k in text_expr_regex.keys():
					expression = re.sub(text_expr_regex[k], k, expression)

	 		code = parser.expr(expression).compile()	# Code injection safe eval.
	 		val = eval(code)


 	return str(val)
