import sys
import os
import argparse
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
from scrapyprj.database.settings import markets as dbsettings
from scrapyprj.database.markets.orm.models import *
from scrapyprj.database import db
from IPython import embed
from datetime import datetime
from scrapyprj.spiders.MarketSpider import MarketSpider



def maincrawl(r, crawlerprocess, spider_attr):
	for i in range(0,args.instances):
		crawlerprocess.crawl(args.spider, **spider_attr)	# Launch the spider.

def start_dbprocess():
	dbprocess = Process()
	dbprocess.start = datetime.now()
	dbprocess.pid = os.getpid()
	dbprocess.cmdline = ' '.join(sys.argv)
	dbprocess.save()

	return dbprocess

def end_dbprocess(r, dbprocess):
	dbprocess.end = datetime.now()
	dbprocess.save()

if __name__ == '__main__':
	
	parser = argparse.ArgumentParser()

	parser.add_argument('--spider',  required=True, help='The spider name to launch')
	parser.add_argument('--instances', default=1, type=int, help='Number of instance of the spider to launch')
	parser.add_argument('--login', nargs='*', help='List of logins to use by the spider. Each item represent to name of the key in the spider settings file.')

	args = parser.parse_args()

	settings = get_project_settings()

	db.init(dbsettings);

	settings.set('login', args.login)	# List of allowed login to use
	
	crawlerprocess = CrawlerProcess(settings)
	dbprocess = start_dbprocess()	# Create an Process entry in the database. We'll pass this object to the spider so we knows they have been launched together.
	spider_attributes = {
			'process' : dbprocess,
			'dao' : MarketSpider.make_dao()	# DAO is shared between spider.
		}

	for i in range(0,args.instances):
		crawlerprocess.crawl(args.spider, **spider_attributes)
	
	crawlerprocess.start() # the script will block here until the crawling is finished

