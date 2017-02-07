import re
import parser
def Answer(q, qhash=None):
	answer = "yes"
	q=q.strip()
 	
	if qhash:
		pass #Check database for hashes

 	if q.startswith('Solve'):
		r = re.compile("Solve (.*)")
		q = q.replace('x', '*')
 		m = r.match(q)	# Math question of type "Solve 5 + (2 x 3)"
	 	if m:
	 		code = parser.expr(m.group(1)).compile()	# Code injection safe eval.
	 		answer = eval(code)

	 

 	return answer
