import sys
import os
import argparse
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
from scrapyprj.database.orm.models import *
from scrapyprj.database import db
from IPython import embed
from datetime import datetime



def maincrawl(r, crawlerprocess, spider_attr):
	settings.set('indexingmode', False)
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
	parser.add_argument('--mode', default='delta', choices=['delta', 'full'], help='The crawling mode. Full to fetch everything. Delta to fetch only from last scrape (or specified time)')
	parser.add_argument('--delta_fromtime', nargs='?', help='Datetime. When doing delta crawl, only items modified after this date will be crawled. If not specified, start time of previous crawl will be used.')
	parser.add_argument('--login', nargs='*', help='List of logins to use by the spider. Each item represent to name of the key in the spider settings file.')

	args = parser.parse_args()

	settings = get_project_settings()

	db.init(settings['DATABASE']);

	settings.set('login', args.login)	# List of allowed login to use

	if args.mode == 'delta' and args.delta_fromtime:
		settings.set('deltamode', True)
		settings.set('deltafromtime',args.delta_fromtime)
	else:
		settings.set('deltamode', False)

	crawlerprocess = CrawlerProcess(settings)
	dbprocess = start_dbprocess()	# Create an Process entry in the database. We'll pass this object to the spider so we knows they have been launched together.

	indexingscrape = None
	if args.instances > 1:
		settings.set('indexingmode', True)
		crawlerprocess.crawl(args.spider, process=dbprocess)	# Indexing spider task is in the queue
		indexingscrape = Scrape.select().where(Scrape.process == dbprocess).get()

	d = crawlerprocess.join()	#Get the defered call when all tasks are completed.
	
	spider_attributes = {
		'process' : dbprocess,
		'indexingscrape' : indexingscrape,
		'spidercount' : args.instances
	}


	d.addCallback(maincrawl, crawlerprocess, spider_attributes)	# Will launch all spiders once the indexing spider is done.
	d.addCallback(end_dbprocess, dbprocess)		# Will save the process to the database
	
	
	crawlerprocess.start() # the script will block here until the crawling is finished

