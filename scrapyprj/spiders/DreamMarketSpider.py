from scrapyprj.spiders.MarketSpider import MarketSpider



class DreamMarketSpider(MarketSpider):
	name = "dreammarket"

	def __init__(self, *args, **kwargs):
		super(MarketSpider, self).__init__( *args, **kwargs)


	def start_requests(self):
		print "yeah"