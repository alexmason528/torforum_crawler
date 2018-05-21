# coding=utf-8
from scrapyprj.spiders.MarketSpiderV2 import MarketSpiderV2
from scrapy.shell import inspect_response
from scrapy.http import FormRequest,Request
import scrapy
import re
from IPython import embed
import parser
import scrapyprj.items.market_items as items
import json
import scrapyprj.database.markets.orm.models as dbmodels
from datetime import datetime, timedelta, date
from urlparse import urlparse, parse_qsl
import dateutil.parser


class FlugsvampMarketSpider(MarketSpiderV2):
    name = "flugsvamp_market"
    custom_settings = {
        'IMAGES_STORE' : './files/img/flugsvamp_market',
        'RANDOMIZE_DOWNLOAD_DELAY' : True,
        'HTTPERROR_ALLOW_ALL' : True,
        'RETRY_ENABLED' : True,
        'RETRY_TIMES' : 5,
        'MAX_LOGIN_RETRY' : 10
    }

    def __init__(self, *args, **kwargs):
        super(FlugsvampMarketSpider, self).__init__( *args, **kwargs)
        self.set_max_concurrent_request(1)      # Scrapy config
        self.set_download_delay(10)             # Scrapy config
        self.set_max_queue_transfer_chunk(16)    # Custom Queue system
        self.statsinterval        = 60          # Custom Queue system
        # Marketspider2 settings.
        self.recursive_flag       = False # Same as self.islogged-flag in ForumSpiderV3.
        self.report_status        = True
        self.report_other_hostnames = False
        # Custom for this spider.
        self.captcha_trial        = 0
        self.logintrial           = 0

    def start_requests(self):
        yield self.make_request(reqtype = 'index', dont_filter = True, shared = False)

    def make_request(self, reqtype='regular', **kwargs):
        if 'url' in kwargs:
            kwargs['url'] = self.make_url(kwargs['url'])
        if reqtype == 'index':
            req = Request(self.make_url('index'), headers = self.tor_browser)
            req.dont_filter=True
            req.meta['shared'] = False
        elif reqtype == 'loginpage':
            req = Request(self.make_url('login'), headers = self.tor_browser)
            req.meta['shared'] = False
        elif reqtype == 'dologin':
            req = self.request_from_login_page(kwargs['response'])
            req.meta['shared'] = False
        elif reqtype == 'image':
            req = Request(self.make_url(kwargs['url']))
            req.meta['shared'] = False
            req.dont_filter    = True           
        # Using kwargs you can set a regular request to not being shared.
        elif reqtype == 'regular':
            req = Request(self.make_url(kwargs['url']), headers = self.tor_browser)
        # Set sharing.
        if 'shared' in kwargs:
            req.meta['shared'] = kwargs['shared']
        elif reqtype == 'regular':
            req.meta['shared'] = True
        else:
            req.meta['shared'] = False

        req.meta['reqtype'] = reqtype 
        req.meta['proxy']   = self.proxy  
        req.meta['slot']    = self.proxy

        if 'dont_filter' in kwargs:
            req.dont_filter = kwargs['dont_filter']
        if 'priority' in kwargs:
            req.priority = kwargs['priority']
        if 'req_once_logged' in kwargs:
            req.meta['req_once_logged'] = kwargs['req_once_logged']

        return self.set_priority(req)

    def parse_response(self, response):
        parser = None
        if self.islogged(response) is False:
            self.recursive_flag = False
            req_once_logged = response.meta['req_once_logged'] if 'req_once_logged'  in response.meta else response.request
            if self.is_login_page(response) is True:
                self.logger.warning("%s: On login page. Proceeding to log in. Have used %s attempts." % (self.login['username'], self.logintrial))
                self.logintrial += 1
                if self.logintrial > self.settings['MAX_LOGIN_RETRY']:
                    self.wait_for_input("Too many login failed", req_once_logged)
                    self.logintrial = 0
                    return                  
                yield self.make_request(reqtype = 'dologin', response=response, dont_filter = True, req_once_logged = req_once_logged)
            elif self.islogged(response) is False and self.is_login_page(response) is False:
                self.logintrial = 0
                yield self.make_request(reqtype = 'loginpage', dont_filter = True, req_once_logged = req_once_logged)
            else:
                self.logger.warning('This is not supposed to happen.')

        elif self.islogged(response) is True:
            self.recursive_flag = True
            self.logintrial     = 0
            if response.meta['reqtype'] == 'dologin':
                self.logger.info("Succesfully logged in as %s! Setting parsing flag." % (self.login['username']))
            if self.is_ads(response):
                if self.is_multilisting(response):
                    parse = self.parse_multiADs
                else:
                    parser = self.parse_ads

            if parser is not None:
                for x in parser(response):
                    yield x

        else:
            self.logger.warning('Outside blocks: This is not supposed to happen. HTML %s' % response.body)

    ############### FLAGS #################
    def islogged(self, response):
        if "Logga ut" in response.body:
            return True
        else: 
            return False

    def is_login_page(self, response):
        login_form = response.xpath('//div[@id="loginform"]')
        if len(login_form) == 1:
            return True
        else: 
            return False        

    def is_ads(self, response):
        if "index.php?p=" in response.url:
            return True

    def is_multilisting(self, response):
        adList = response.xpath('//select[@name="adlist"]')
        if len(adList) == 1:
            return True
        else:
            return False

    ############# REQUEST CREATION ################
    def request_from_login_page(self, response):
        data = {
            'username' : self.login['username'],
            'password' : self.login['password']
        }
        req = FormRequest.from_response(response, formdata = data, headers = self.tor_browser)

        return req

    ########## PARSERS ###############
    def parse_ads(self, response):
        title = response.xpath(".//div[@id='main']/h1/text()").extract_first()
        if title is None and response.xpath(".//div[contains(text(), 'Produkten finns inte.')]"):
            self.logger.warning("Found what is likely an empty page at %s. Flugsvamp writes: %s" % (response.url, response.xpath(".//div[contains(text(), 'Produkten finns inte.')]/text()").extract_first().strip()))
        else:
            ads_item                = items.Ads()
            user_item               = items.User()
            ads_item['title']       = title
            ads_item['offer_id']    = response.url.split("=")[-1]
            ads_item['fullurl']     = response.url
            ads_item['relativeurl'] = self.get_relative_url(response.url)

            # COMMENT WHY THIS IS.
            description = self.get_text(response.xpath('//strong[contains(text(), "Beskrivning:")]/parent::div')).replace('Beskrivning:', '')
            if description:
                ads_item['description'] = description
            try:
                keys = response.xpath(".//div[@class='lightrow']")
                for key_ele in keys:
                    key = key_ele.xpath("strong/text()").extract_first()
                    if key == None:
                        continue
                    key = key.lower()
                    if "omd" in key:
                        value   = key_ele.xpath('.//span[@class="grey"]/text()').extract_first()
                        m       = re.search('(.*?)\ \((.*?)\ omd', value, re.M|re.I|re.S)
                        if m:
                            ads_item['product_rating']  = m.group(1)
                            ads_item['already_sold']    = m.group(2)
                    elif "ljare" in key:
                        ads_item['vendor_username']     = key_ele.xpath('.//a/text()').extract_first()
                        user_item['username']           = ads_item['vendor_username']
                        user_item['relativeurl']        = key_ele.xpath('.//a/@href').extract_first()
                        user_item['fullurl']            = response.urljoin(user_item['relativeurl'])
                        value                           = key_ele.xpath('.//span[@class="grey"]/text()').extract_first()
                        m                               = re.search('(.*?)\ \((.*?)\ omd', value, re.M|re.I|re.S)
                        if m:
                            user_item['average_rating']     = m.group(1)
                            user_item['feedback_received']  = m.group(2)                    
                    elif key == "kategori:":
                        ads_item['category'] = key_ele.xpath('.//a/text()').extract_first()
                    elif key == "kvantitet:":
                        ads_item['quantity'] = self.get_text(key_ele.xpath('span[@class="float-right"]'))
                    elif key == "ditt pris inkl. frakt:":
                        value = self.get_text(key_ele.xpath('.//span[@class="float-right"]'))
                        m = re.search('(.*?)\ \((.*?)\)', value, re.M|re.I|re.S)
                        if m:
                            ads_item['price_btc'] = m.group(2)
                    elif key == "pristabell:":
                        price_options   = []
                        priceList       = key_ele.xpath('.//span[@class="float-right"]').extract_first().split('<br>')
                        for list_item in priceList:
                            linesel     = scrapy.Selector(text=list_item)
                            line_txt    = self.get_text(linesel)                            
                            price_options.append(line_txt)
                        if len(price_options) > 0:
                            ads_item['price_options'] = price_options                        
                    else:
                        self.logger.warning("Found a new piece of product information, '%s', at %s" % (key, response.url))
                yield ads_item
                yield user_item
            except Exception as error:
                self.logger.warning("Failed to parse listing (Error: '%s'). See URL %s" % (error, response.url))

        # ===================== IMAGES =====================
        images_url = response.css('img.float-right::attr(src)').extract();
        for url in images_url:
            if url:
                img_item = items.AdsImage(image_urls = [])
                img_item['image_urls'].append(self.make_request(reqtype = 'image', url=url, headers = self.tor_browser))
                img_item['ads_id'] = ads_item['offer_id']
                yield img_item

    def parse_multiADs(self, response):
        for element in response.xpath('//select[@name="adlist"]/option'):
            adlist_param = element.xpath('@value').extract_first()
            multiLink = self.spider_settings['endpoint'].format(adlist_param)
            yield self.make_request(url=multiLink, headers = self.tor_browser)