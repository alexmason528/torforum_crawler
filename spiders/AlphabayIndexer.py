from __future__ import absolute_import
import scrapy
from scrapy.conf import settings
import torforum_crawler.thirdparties.deathbycaptcha as deathbycaptcha

class AlphabayIndexer(scrapy.Spider):
    name = "alphabay_indexer"
    dbc = deathbycaptcha.SocketClient(settings['DEATHBYCAPTHA']['username'],settings['DEATHBYCAPTHA']['password'])
    
    def __init__(self, *args, **kwargs):
        self.dbc= deathbycaptcha.SocketClient('a', 'b');

        super(AlphabayIndexer, self).__init__(*args, **kwargs)

    def start_requests(self):
        urls  = [
            'http://pwoah7foa6au2pul.onion'
        ]

        for url in urls :
            yield self.get_request(url)

    def parse(self, response):
        pass
        #print response.body

    def get_request(self, url):
        req = scrapy.Request(url=url, callback=self.parse)
        proxy = getattr(self, 'proxy', None)
        if proxy:
            req.meta['proxy'] = proxy
        return req