from scrapy.http import Request

class ReplayRequest(Request):
	def __init__(self, response, *args, **kwargs):
		super(ReplayRequest, self).__init__(*args, **kwargs)
		self.response = response