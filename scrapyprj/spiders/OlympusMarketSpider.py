# coding=utf-8

from scrapyprj.spiders.MarketSpiderV2 import MarketSpiderV2
from scrapy.http import FormRequest,Request
import re
import scrapyprj.items.market_items as items
from scrapy.shell import inspect_response
# For http 302 handling
from scrapy.utils.python import to_native_str
from six.moves.urllib.parse import urljoin

class OlympusMarketSpider(MarketSpiderV2):
    name = "olympus_market"
    custom_settings = {
        'IMAGES_STORE'              : './files/img/olympus_market',
        'RANDOMIZE_DOWNLOAD_DELAY'  : True,
        'HTTPERROR_ALLOW_ALL'       : True,
        'RETRY_ENABLED'             : True,
        'RETRY_TIMES'               : 5,
        'MAX_LOGIN_RETRY'           : 10,
    }
    handle_httpstatus_list = [302]

    def __init__(self, *args, **kwargs):
        super(OlympusMarketSpider, self).__init__( *args, **kwargs)
        self.set_max_concurrent_request(1)      # Scrapy config
        self.set_download_delay(20)             # Scrapy config
        self.set_max_queue_transfer_chunk(1)    # Custom Queue system
        self.statsinterval        	= 60		# Custom Queue system
        # Marketspider2 settings.
        self.recursive_flag 	  	= False # Same as self.islogged-flag in ForumSpiderV3.
        self.report_status 		  	= True
        self.report_other_hostnames = False
        self.logintrial 		  	= 0 
        self.http_errors            = 0

    def start_requests(self):
        yield self.make_request(reqtype = 'index', dont_filter = True, shared = False)

    def make_request(self, reqtype='regular', **kwargs):
        if 'url' in kwargs:
            kwargs['url'] = self.make_url(kwargs['url'])

        if reqtype == 'index':
            req = Request(self.make_url('index'), headers = self.tor_browser)
            req.meta['shared']  = False
            req.dont_filter	   	= True
        elif reqtype == 'loginpage':
            req = Request(self.make_url('login'), headers = self.tor_browser)
            req.dont_filter	   	= True			
            req.meta['shared']  = False
        elif reqtype == 'dologin':
            req = self.request_from_login_page(kwargs['response'])
            req.meta['shared']  = False
        elif reqtype == 'image':
            req = Request(kwargs['url'], headers = self.tor_browser)
        elif reqtype == 'regular':
            req = Request(kwargs['url'], headers = self.tor_browser)

        # Set sharing.
        if 'shared' in kwargs:
            req.meta['shared'] = kwargs['shared']
        elif reqtype == 'regular':
            req.meta['shared'] = True
        else:
            req.meta['shared'] = False

        # Using kwargs you can set a regular request to not being shared.
        if 'dont_filter' in kwargs:
            req.dont_filter = kwargs['dont_filter']
        if 'priority' in kwargs:
            req.priority = kwargs['priority']
        if 'req_once_logged' in kwargs:
            req.meta['req_once_logged'] = kwargs['req_once_logged']
        if 'ads_id' in kwargs:
            req.meta['ads_id'] = kwargs['ads_id']

        # Some default'ish options.
        req.meta['reqtype'] = reqtype 
        req.meta['proxy']   = self.proxy  
        req.meta['slot']    = self.proxy
            
        return self.set_priority(req)

    def parse_response(self, response):
        parser = None
        if response.status >= 300 and response.status < 400:
            self.recursive_flag = False
            location        = to_native_str(response.headers['location'].decode('latin1'))
            request         = response.request
            redirected_url  = urljoin(request.url, location)
            req             = self.make_request(url = redirected_url, dont_filter = True, shared = False)
            if response.meta['reqtype']:
                req.meta['reqtype'] = response.meta['reqtype']
            req.meta['req_once_logged'] = response.meta['req_once_logged'] if 'req_once_logged' in response.meta else response.request
            req.priority                = 50
            self.logger.warning("%s: Being redirected from %s to %s. [Priority: %s | Shared: %s]" % (self.login['username'], request.url, req.url, req.priority, req.meta['shared']))
            yield req        
        elif self.islogged(response) is False:
            self.recursive_flag = False
            req_once_logged = response.meta['req_once_logged'] if 'req_once_logged' in response.meta else response.request
            if response.url.endswith(".png") is True or response.meta['reqtype'] == 'image':
                pass
            elif self.is_login_page(response) is True:
                login_error = self.get_text(response.xpath(".//div[@class='alert alert-danger']")) # Catch and print the error message.
                
                if len(login_error) > 0:
                    self.logger.warning("Got login error: %s" % login_error)

                self.logger.warning("%s: On login page. Proceeding to log in. Have used %s attempts." % (self.login['username'], self.logintrial))
                self.logintrial += 1

                if self.logintrial > self.settings['MAX_LOGIN_RETRY']:
                    self.wait_for_input("Too many login failed", req_once_logged)
                    self.logintrial = 0
                    return

                yield self.make_request(reqtype = 'dologin', response=response, dont_filter = True, req_once_logged = req_once_logged)

            elif self.is_login_page(response) is False:
                self.logger.warning("%s: Going to login page." % self.login['username'])
                self.logintrial = 0

                yield self.make_request(reqtype = 'loginpage', req_once_logged = req_once_logged, dont_filter = True)
        else:
            self.recursive_flag = True
            self.logintrial     = 0
            if response.meta['reqtype'] == 'dologin':
                self.logger.info("Succesfully logged in as %s! Setting parsing flag." % (self.login['username']))

            if self.is_product_page(response) is True:
                parser = self.parse_product
            elif self.is_product_tac_page(response) is True:
                parser = self.parse_product_tac
            elif self.is_product_rating_page(response) is True:
                parser = self.parse_product_rating
            elif self.is_user_page(response) is True:
                parser = self.parse_user

            if parser is not None:
                for x in parser(response):
                    yield x

    ############### FLAGS #################
    def islogged(self, response):
        if 'Logged in as' in response.body:
            return True
        else:
            return False

    def is_login_page(self, response):
        return 'signin' in response.url

    def is_product_page(self, response):
        if re.search('/listings/[\w-]+/[\w-]+$', response.url):
            return True
        return False

    def is_product_tac_page(self, response):
        if re.search('/listings/[\w-]+/[\w-]+/refund_policy$', response.url):
            return True
        return False

    def is_product_rating_page(self, response):
        if re.search('/listings/[\w-]+/[\w-]+/feedback', response.url):
            return True
        return False

    def is_user_page(self, response):
        if re.search('/profile/view/[\w-]+$', response.url):
            return True
        return False

    def request_from_login_page(self, response):
        data = {
            'username' : self.login['username'],
            'password' : self.login['password']
        }
        req             = FormRequest.from_response(response, formdata = data, headers = self.tor_browser)
        captcha_src     = response.css('form img::attr(src)').extract_first()
        req.meta['captcha'] = {
            'request'   : self.make_request(url=captcha_src, headers = self.tor_browser, dont_filter=True),
            'name'      : 'captcha'
        }
        return req

    ########## PARSERS ###############
    def parse_product(self, response):
        try:
            username                            = self.get_text(response.css('h4.media-heading a'))
            offer_id                            = re.search(r'/listings/[\w-]+/([\w-]+)$', response.url).group(1)
            title                               = self.get_text(response.css('h3.m-b-15'))
            ads_item                            = items.Ads()
            ads_item['vendor_username']         = username
            ads_item['offer_id']                = offer_id
            ads_item['title']                   = title
            ads_item['relativeurl']             = self.get_relative_url(response.url)
            ads_item['fullurl']                 = response.url
            prices = response.xpath(".//div[@class='panel-footer text-center']").extract_first()
            ads_item['accepted_currencies']     = []
            price_usd = re.search("([0-9\.]*) USD", prices)
            price_xmr = re.search("([0-9\.]*) XMR", prices)
            price_btc = re.search("([0-9\.]*) BTC\n", prices)
            if price_usd:
                ads_item['price_usd'] = price_usd.group(1)
            if price_xmr:
                ads_item['price_xmr'] = price_xmr.group(1)
                ads_item['accepted_currencies'].append("xmr")
            if price_btc:
                ads_item['price_btc'] = price_btc.group(1)
                ads_item['accepted_currencies'].append("btc")

            dts = response.css("dl.dl-horizontal dt")            
            for dt in dts:
                key = self.get_text(dt).lower()
                value = self.get_text(dt.xpath('following-sibling::dd[1]'))
                if key == 'sold':
                    ads_item['already_sold'] = re.search(r'(\d+)', value).group(1)
                elif key == 'ships from':
                    ads_item['ships_from'] = value
                elif key == 'ships to':
                    ads_item['ships_to'] = value
                elif key == 'payment type':
                    ads_item['escrow'] = value
                    if 'multisig' in value.lower():
                        ads_item['multisig'] = True
                elif key == 'product type':
                    ads_item['category'] = value
                elif key in ['sold by', 'trust rating', 'creation date', 'starts from']:
                    pass
                else:
                    self.logger.warning('New information found on use profile page : %s' % key)

            ads_item['shipping_options']        = []
            for option in response.css('select#shipping_method option'):
                ads_item['shipping_options'].append(self.get_text(option))

            ads_item['description'] = self.get_text(response.css('p.break-me'))

            yield ads_item
        except Exception as error:
            self.logger.warning("Failed to yield ads at %s because '%s'" % (response.url, error))

        try:
            # Yield images in thumbnail.
            images_url = response.css('a.thumbnail img::attr(src)').extract()
            for url in images_url:
                if url:
                    ads_image               = items.AdsImage(image_urls = [])
                    ads_image['ads_id']     = offer_id
                    ads_image['image_urls'].append(self.make_request(reqtype = 'regular', url=url))
                    yield ads_image

            # Yield feature image.
            image_url = response.css('img.featured-image::attr(src)').extract_first()

            if image_url:
                ads_image               = items.AdsImage(image_urls = [])
                ads_image['ads_id']     = offer_id
                ads_image['image_urls'].append(self.make_request(reqtype = 'regular', url=image_url))
                yield ads_image

        except Exception as error:
            self.logger.warning("Failed to yield images at %s because '%s'" % (response.url, error))


    def parse_product_tac(self, response):
        try:
            username        = self.get_text(response.css('h4.media-heading a'))
            offer_id        = re.search(r'/listings/[\w-]+/([\w-]+)/refund_policy', response.url).group(1)
            title           = self.get_text(response.css('h3.m-b-15'))
            tac             = self.get_text(response.css('div.product-details > div > div')[2])
            url             = response.url.replace("/refund_policy", "")

            ads_item                            = items.Ads()
            ads_item['vendor_username']         = username
            ads_item['offer_id']                = offer_id
            ads_item['title']                   = title
            ads_item['terms_and_conditions']    = tac
            ads_item['relativeurl']             = self.get_relative_url(url)
            ads_item['fullurl']                 = url            

            yield ads_item

        except Exception as error:
            self.logger.warning("Failed to yield ads terms and conditions at %s because '%s'" % (response.url, error))

    def parse_product_rating(self, response):
        try:
            ads_id        = re.search(r'/listings/[\w-]+/([\w-]+)/feedback', response.url).group(1)
            ratings       = response.css('div.product-details table.table tbody tr')

            for rating in ratings:
                tds                                     = rating.css('td')
                product_rating                          = items.ProductRating()
                product_rating['submitted_by']          = self.get_text(tds[0])
                product_rating['rating']                = len(tds[1].css('i'))
                product_rating['comment']               = self.get_text(tds[2])
                product_rating['submitted_on']          = self.parse_datetime(self.get_text(tds[3])).date()
                product_rating['submitted_on_string']   = self.get_text(tds[3])
                product_rating['ads_id']                = ads_id
                yield product_rating

        except Exception as error:
            self.logger.warning("Failed to yield product rating at %s because '%s'" % (response.url, error))


    def parse_user(self, response):
        
        try:
            last_active_span        = response.css('.panel-heading .row div:nth-child(2) span')
            last_active             = self.parse_datetime(re.search(r'Last seen: (.+)', self.get_text(last_active_span)).group(1))

            user                                = items.User()
            user['username']                    = self.get_text(response.css('.breadcrumb li.active'))
            user['relativeurl']                 = self.get_relative_url(response.url)
            user['fullurl']                     = response.url
            user['profile']                     = self.get_text(response.css('#profile .col-md-9'))
            user['average_rating']              = self.get_text(response.css('center span')[0])
            user['last_active']                 = last_active
            user['terms_and_conditions']        = self.get_text(response.css('#tac .col-md-9'))
            user['public_pgp_key']              = self.normalize_pgp_key(self.get_text(response.css('#pgp pre.well')))

            level_match = re.search('Level (\d+)', self.get_text(response.css('.label-success')))

            if level_match:
                user['level'] = level_match.group(1)
            if 'FE' in response.xpath(".//div/span[@class='label label-default']/text()").extract():
                user['fe_enabled'] = True
            else:
                user['fe_enabled'] = False
            dream_rating = response.xpath(".//small[preceding-sibling::img[contains(@title, 'Dream')]]/text()")
            if dream_rating:
                dream_rating                = dream_rating.extract_first()
                user['dreammarket_sales']   = re.search("([0-9]*),", dream_rating).group(1)
                user['dreammarket_rating']  = re.search(", ([0-9\.]*)", dream_rating).group(1)

            yield user
        except Exception as error:
            self.logger.warning("Failed to yield user at %s because '%s'" % (response.url, error))

        try:
            ratings = response.xpath(".//div[@id='feedback']/div/div/div/table[1]/tbody/tr")
            if ratings and 'No available feedback' not in ratings.extract_first():
                for rating in ratings:
                    tds                                 = rating.css('td')
                    user_rating                         = items.UserRating()
                    user_rating['username']             = user['username']
                    user_rating['submitted_by']         = self.get_text(tds[0])
                    user_rating['rating']               = len(tds[1].css('i'))
                    user_rating['comment']              = self.get_text(tds[2])
                    user_rating['price_usd']            = re.search('([\d\.]+)', self.get_text(tds[3])).group(1)
                    user_rating['submitted_on']         = self.parse_datetime(self.get_text(tds[4])).date()
                    user_rating['submitted_on_string']  = self.get_text(tds[4])
                    yield user_rating

        except Exception as error:
            self.logger.warning("Failed to yield user ratings at %s because '%s'" % (response.url, error))


