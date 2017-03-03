from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
import sys
import argparse
from scrapy.spiderloader import SpiderLoader
from IPython import embed

parser = argparse.ArgumentParser()

parser.add_argument('--instances', default=1, help='Number of instance of the spider to launch')
parser.add_argument('--spider',  help='The spider name to launch')
parser.add_argument('--mode', default='delta', choices=['delta', 'full'], help='The crawling mode. Full to fetch everything. Delta to fetch only from last scrape (or specified time)')
parser.add_argument('--delta_fromtime', nargs='?', help='Datetime. When doing delta crawl, only items modified after this date will be crawled. If not specified, start time of previous crawl will be used.')

args = parser.parse_args()

settings = get_project_settings()

settings.set('crawlmode',args.mode)

if args.mode == 'delta' and args.delta_fromtime:
	settings.set('fromtime',args.delta_fromtime)

process = CrawlerProcess(settings)

for i in range(0,10):
	process.crawl(args.spider)	# Launch the spider.
process.start() # the script will block here until the crawling is finished
