# coding=utf-8
from scrapy.shell import inspect_response
from scrapyprj.spiders.MarketSpiderV2 import MarketSpiderV2
from scrapy.http import FormRequest, Request
import re
import scrapyprj.items.market_items as items

class BerlusconiMarket(MarketSpiderV2):
    name = "berlusconi_market"
    custom_settings = {
        'IMAGES_STORE'              : './files/img/berlusconi_market',
        'RANDOMIZE_DOWNLOAD_DELAY'  : True,
        'HTTPERROR_ALLOW_ALL'       : True,
        'RETRY_ENABLED'             : True,
        'RETRY_TIMES'               : 5,
        'MAX_LOGIN_RETRY'           : 10,
    }

    def __init__(self, *args, **kwargs):
        super(BerlusconiMarket, self).__init__( *args, **kwargs)
        self.set_max_concurrent_request(1)      # Scrapy config
        self.set_download_delay(10)             # Scrapy config
        self.set_max_queue_transfer_chunk(1)    # Custom Queue system
        self.statsinterval        	= 60			# Custom Queue system
        # Marketspider2 settings.
        self.recursive_flag 	  	= False # Same as self.islogged-flag in ForumSpiderV3.
        self.report_status          = True
        self.report_other_hostnames = False
        # Custom for this spider.
        self.logintrial = 0

    def start_requests(self):
        yield self.make_request(reqtype = 'index', dont_filter = True, shared = False)

    def make_request(self, reqtype='regular', **kwargs):
        if 'url' in kwargs:
            kwargs['url'] = self.make_url(kwargs['url'])

        if reqtype == 'index':
            req = Request(self.make_url('index'), headers = self.tor_browser)
            req.dont_filter	   	= True
            req.meta['shared']  = False
        elif reqtype == 'loginpage':
            req = Request(self.make_url('login'), headers = self.tor_browser)
            req.dont_filter	   	= True
            req.meta['shared']  = False
        elif reqtype == 'dologin':
            req = self.request_from_login_page(kwargs['response'])
            req.dont_filter     = True
            req.meta['shared']  = False
        elif reqtype == 'captcha_img':
            req = Request(kwargs['url'])
            req.dont_filter     = True
            req.meta['shared']  = False
        elif reqtype == 'image':
            req = Request(kwargs['url'], headers = self.tor_browser)
            req.meta['shared'] = True
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
        
        if response.status == 404:
        	self.logger.warning("Received 404 response. Error message: %s" % self.get_text(response.xpath(".//h1")))
        
        if self.islogged(response) is False:
            self.recursive_flag = False
            req_once_logged = response.meta['req_once_logged'] if 'req_once_logged'  in response.meta else response.request
            
            if self.is_login_page(response) is True:
                login_error = self.get_text(response.xpath(".//div[@class='alert alert-danger']"))
                
                if len(login_error) > 0:
                    self.logger.warning("Got login error: %s" % login_error)

                self.logger.warning("%s: On login page. Proceeding to log in." % (self.login['username']))
                self.logintrial += 1

                if self.logintrial > self.settings['MAX_LOGIN_RETRY']:
                    self.wait_for_input("Too many login failed", req_once_logged)
                    self.logintrial = 0
                    return

                yield self.make_request(reqtype = 'dologin', response=response, dont_filter = True, req_once_logged=req_once_logged)

            elif self.islogged(response) is False:
                self.logger.warning("%s: Going to login page." % (self.login['username']))
                self.logintrial = 0
                yield self.make_request(reqtype = 'loginpage', req_once_logged=req_once_logged, dont_filter = True)

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
            elif self.is_user_tac_page(response) is True:
                parser = self.parse_user_tac
            elif self.is_user_pgp_page(response) is True:
                parser = self.parse_user_pgp

            if parser is not None:
                for x in parser(response):
                    yield x

    ############### FLAGS #################
    def islogged(self, response):
        return 'Logout' in response.body

    def is_login_page(self, response):
        return 'login' in response.url

    def is_product_page(self, response):
        if re.search('c=listings&a=product&code=[\w]+$', response.url):
            return True
        return False

    def is_product_tac_page(self, response):
        if re.search('c=listings&a=product&code=[\w]+&tab=2$', response.url):
            return True
        return False

    def is_product_rating_page(self, response):
        if re.search('c=listings&a=product&code=[\w]+&tab=3', response.url):
            return True
        return False

    def is_user_page(self, response):
        if re.search('c=listings&a=vendor&v_id=[\w]+$', response.url):
            return True
        return False

    def is_user_tac_page(self, response):
        if re.search('c=listings&a=vendor&v_id=[\w]+&tab=2$', response.url):
            return True
        return False

    def is_user_pgp_page(self, response):
        if re.search('c=listings&a=vendor&v_id=[\w]+&tab=3$', response.url):
            return True
        return False

    def is_user_rating_page(self, response):
        if re.search('c=listings&a=vendor&v_id=[\w]+&tab=4', response.url):
            return True
        return False


    def request_from_login_page(self, response):
        data = {
            'name'      : self.login['username'],
            'password'  : self.login['password']
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
        ads_id = re.search('code=([\w]+)', response.url).group(1)
        try:
            ads_item                            = items.Ads()
            ads_item['offer_id']                = ads_id
            ads_item['title']                   = self.get_text(response.xpath(".//div[@class='col-md-8']/h2"))
            ads_item['relativeurl']             = self.get_relative_url(response.url)
            ads_item['fullurl']                 = response.url
            ads_item['accepted_currencies']   	= response.css('.well input[name="currency"]::attr(value)').extract()
            ads_item['description']         	= self.get_text(response.css('ul.nav-tabs').xpath('following-sibling::p'))

            in_stock_match 						= re.search('(\d+)', response.css('.listing-stock span::text').extract_first())
            if in_stock_match:
                ads_item['in_stock'] 			= in_stock_match.group(1)
            ads_item['shipping_options']        = []
            for option in response.css('select[name="shipping_option"] option'):
                ads_item['shipping_options'].append(self.get_text(option))
            item_sold_match = re.search('(\d+) items sold since ([\d\-: ]+)', self.get_text(response.css('table.table-condensed tr:last-child td')))
            if item_sold_match:
                ads_item['already_sold'] = item_sold_match.group(1)

            trs = response.css('div.col-sm-7 table.table-condensed tr')
            for tr in trs:
                tds = tr.css('td')
                if len(tds) == 2:
                    key = self.get_text(tds[0]).lower()
                    value = self.get_text(tds[1])
                    if key == 'vendor':
                        ads_item['vendor_username'] = tds.xpath(".//a/text()").extract_first()
                    elif key == 'class':
                        ads_item['ads_class'] = value
                    elif key == 'escrow type':
                        ads_item['escrow'] = value
                    elif key == 'ships from':
                        ads_item['ships_from'] = value
                    else:
                        self.logger.warning('New information found on product page : %s' % key)

            prices = self.get_text(response.xpath(".//div[@class='listing-price']"))
            price_eur = re.search("([0-9\.]*) EUR", prices)
            price_usd = re.search("([0-9\.]*) USD", prices)
            if price_usd:
                ads_item['price_usd'] = price_usd.group(1)
            if price_eur:
                ads_item['price_eur'] = price_eur.group(1)
            price_btc = response.xpath(".//div[@class='listing-price']/span").extract_first()
            if 'btc' in price_btc:
            	ads_item['price_btc'] = self.get_text(response.xpath(".//div[@class='listing-price']/span"))
            else:
            	self.logger.warning("Couldn't match BTC price. There might be another currency available. Please inspect %s" % response.url)
            
            yield ads_item
        except Exception as error:
            self.logger.warning("Failed to yield ads at %s because '%s'" % (response.url, error))

        try:
            image_url = response.css('div.index-img img::attr(src)').extract_first()
            if image_url:
                ads_image               = items.AdsImage(image_urls = [])
                ads_image['ads_id']     = ads_id
                ads_image['image_urls'].append(self.make_request('image', url=self.make_url(image_url)))
                yield ads_image
        except Exception as error:
            self.logger.warning("Failed to yield ad image at %s because '%s'" % (response.url, error))

    def parse_product_tac(self, response):
        try:
            ads_item                            = items.Ads()
            ads_item['fullurl']					= re.search("(^.*)&tab", response.url).group(1)
            ads_item['relativeurl']				= self.get_relative_url(ads_item['fullurl'])
            ads_item['vendor_username']         = response.xpath(".//td/a[contains(@href, 'a=vendor')]/text()").extract_first()
            ads_item['offer_id']                = re.search('code=([\w]+)', response.url).group(1)
            ads_item['title']                   = self.get_text(response.xpath(".//div[@class='col-md-8']/h2"))
            ads_item['terms_and_conditions']    = self.get_text(response.css('ul.nav-tabs').xpath('following-sibling::p'))
            yield ads_item
        except Exception as error:
            self.logger.warning("Failed to yield ads terms and conditions at %s because '%s'" % (response.url, error))

    def parse_product_rating(self, response):
        try:
            ads_id        = re.search('c=listings&a=product&code=([\w]+)&tab=3$', response.url).group(1)
            ratings       = response.css('ul.nav-tabs').xpath('following-sibling::table').css('tbody tr')

            for rating in ratings:
                tds                             		= rating.css('td')
                product_rating                  		= items.ProductRating()
                product_rating['ads_id']        		= ads_id
                product_rating['comment']       		= self.get_text(tds[1])
                product_rating['submitted_by']  		= rating.css('td:nth-child(3)::text').extract_first().replace(' ', '')
                product_rating['submitted_on'] 			= self.parse_datetime(self.get_text(tds[3]))
                product_rating['submitted_on_string']   = self.get_text(tds[3])
                prev_transactions 						= rating.xpath(".//small/text()").extract_first()
                prev_transactions						= prev_transactions.replace('[', '')
                prev_transactions						= prev_transactions.replace(']', '')
                product_rating['submitted_by_number_transactions'] = prev_transactions
                price_match = re.search('([\d\.]+) ([\w]+)', self.get_text(tds[4]))
                if price_match:
                    price = price_match.group(1)
                    currency = price_match.group(2).lower()
                    if currency == 'usd':
                        product_rating['price_usd'] = price
                    elif currency == 'xmr':
                        product_rating['price_xmr'] = price
                yield product_rating

        except Exception as error:
            self.logger.warning("Failed to yield product rating at %s because '%s'" % (response.url, error))


    def parse_user(self, response):
        try:
            user                                = items.User()
            user['username']                    = self.get_text(response.css('h1::text').extract_first())
            if user['username'] == '':
            	user['username'] = response.xpath(".//h1/i/del/text()").extract_first()
            if response.xpath(".//h1/i/text()") and 'Banned' in response.xpath(".//h1/i/text()").extract_first():
            	user['is_banned'] = True
            user['relativeurl']                 = self.get_relative_url(response.url)
            user['fullurl']                     = response.url
            user['profile']                     = self.get_text(response.css('ul.nav-tabs').xpath('following-sibling::p'))
            user['positive_feedback']           = self.get_text(response.css('a.no-style')[0].css('strong'))
            user['neutral_feedback']            = self.get_text(response.css('a.no-style')[1].css('strong'))
            user['negative_feedback']           = self.get_text(response.css('a.no-style')[2].css('strong'))
            info 								= self.get_text(response.css('p.text-muted')[0])
            info 								= re.sub('\s+',' ',info)
            user['last_active'] 				= self.parse_datetime(re.search("Last seen - (.*?) UTC", info).group(1))
            user['join_date'] 					= self.parse_datetime(re.search("Vendor since - (.*?) UTC", info).group(1))
            user['ship_from']					= re.search("Ships From - (.*)", info).group(1)
            yield user
        except Exception as error:
            self.logger.warning("Failed to yield user at %s because '%s'" % (response.url, error))

    def parse_user_tac(self, response):
        try:
            user                                = items.User()
            user['username']                    = self.get_text(response.css('h1::text').extract_first())
            if user['username'] == '':
            	user['username'] 				= response.xpath(".//h1/i/del/text()").extract_first()
            user['fullurl']						= re.search("(^.*)&tab", response.url).group(1)
            user['relativeurl']					= self.get_relative_url(user['fullurl'])
            user['terms_and_conditions']        = self.get_text(response.css('ul.nav-tabs').xpath('following-sibling::p'))
            yield user
        except Exception as error:
            self.logger.warning("Failed to yield user Terms & Conditions from %s because '%s'" % (response.url, error))

    def parse_user_pgp(self, response):
        try:
            user                                = items.User()
            user['username']                    = self.get_text(response.css('h1::text').extract_first())
            if user['username'] == '':
            	user['username'] 				= response.xpath(".//h1/i/del/text()").extract_first()
            user['fullurl']						= re.search("(^.*)&tab", response.url).group(1)
            user['relativeurl']					= self.get_relative_url(user['fullurl'])
            user['public_pgp_key']              = self.get_text(response.css('ul.nav-tabs').xpath('following-sibling::p'))
            yield user
        except Exception as error:
            self.logger.warning("Failed to yield user PGP from %s because '%s'" % (response.url, error))