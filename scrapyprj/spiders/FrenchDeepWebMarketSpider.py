# coding=utf-8

from scrapyprj.spiders.MarketSpiderV2 import MarketSpiderV2
from scrapy.http import FormRequest,Request
import re
import scrapyprj.items.market_items as items
from scrapy.shell import inspect_response

class FrenchDeepWebMarketSpider(MarketSpiderV2):
    name = "frenchdeepweb_market"
    custom_settings = {
        'IMAGES_STORE'              : './files/img/frenchdeepweb_market',
        'RANDOMIZE_DOWNLOAD_DELAY'  : True,
        'HTTPERROR_ALLOW_ALL'       : True,
        'RETRY_ENABLED'             : True,
        'RETRY_TIMES'               : 5,
        'MAX_LOGIN_RETRY'           : 50,
    }

    def __init__(self, *args, **kwargs):
        super(FrenchDeepWebMarketSpider, self).__init__( *args, **kwargs)
        self.set_max_concurrent_request(1)      # Scrapy config
        self.set_download_delay(10)             # Scrapy config
        self.set_max_queue_transfer_chunk(1)    # Custom Queue system
        self.statsinterval        	= 60			# Custom Queue system
        # Marketspider2 settings.
        self.recursive_flag 	  	= False # Same as self.islogged-flag in ForumSpiderV3.
        self.report_status 		  	= False
        self.report_other_hostnames = False
        self.logintrial 		  	= 0 

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

        if self.islogged(response) is False:
            self.recursive_flag = False
            # DDoS and login handling block.
            req_once_logged = response.meta['req_once_logged'] if 'req_once_logged'  in response.meta else response.request
            if self.is_login_page(response) is True:

                login_error = self.get_text(response.xpath(".//div[@class='alert alert-danger']")) # Catch and print the error message.

                if len(login_error) > 0:
                    self.logger.warning("Got login error: %s" % login_error)

                self.logger.warning("On login page. Proceeding to log in.")
                self.logintrial += 1

                if self.logintrial > self.settings['MAX_LOGIN_RETRY']:
                    self.wait_for_input("Too many login failed", req_once_logged)
                    self.logintrial = 0
                    return

                yield self.make_request(reqtype = 'dologin', response=response, dont_filter = True, req_once_logged = req_once_logged)

            elif self.is_login_page(response) is False:
                self.logger.warning("Going to login page.")
                self.logintrial = 0
                yield self.make_request(reqtype = 'loginpage', req_once_logged = req_once_logged, dont_filter = True)

        else:
            self.recursive_flag = True
            self.logintrial     = 0

            if response.meta['reqtype'] == 'dologin':
                self.logger.info("Succesfully logged in as %s! Setting parsing flag." % (self.login['username']))

            if self.is_product_page(response) is True:
                parser = self.parse_product
            elif self.is_vendor_page(response) is True:
                parser = self.parse_vendor
            elif self.is_feedback_page(response) is True:
                parser = self.parse_feedback

            if parser is not None:
                for x in parser(response):
                    yield x
            else:
                if response.url != self.make_url('index'):
                    self.logger.info("Unknown page type at %s" % response.url)

    ############### FLAGS #################
    def islogged(self, response):
        login_link = response.xpath('.//a[@href="/logout/"]')
        return len(login_link) == 1

    def is_login_page(self, response):
        login_form = response.xpath(".//form[@action='/login/']")
        return len(login_form) == 1

    def is_product_page(self, response):
        if re.search('/product/[\w-]+/$', response.url):
            return True
        return False

    def is_vendor_page(self, response):
        if re.search('/account/[\w-]+/$', response.url):
            return True
        return False

    def is_feedback_page(self, response):
        if re.search('/feedbacks/feedback_list/[\w-]+/$', response.url):
            return True
        return False

    def request_from_login_page(self, response):
        data = {
            'username' : self.login['username'],
            'password' : self.login['password']
        }
        
        req = FormRequest.from_response(response, formdata = data, headers = self.tor_browser)
        return req

    ########## PARSERS ###############
    def parse_product(self, response):
        try:
            offer_id    = re.search(r'/product/([\w-]+)/$', response.url).group(1)
            title       = re.search(r'produit «(.+)»', self.get_text(response.css('div.card-header h2'))).group(1)

            ads_item                    = items.Ads()
            ads_item['offer_id']        = offer_id
            ads_item['title']           = title
            ads_item['relativeurl']     = self.get_relative_url(response.url)
            ads_item['fullurl']         = response.url

            trs = response.css('table.m-0 tr')

            for tr in trs:
                key     = self.get_text(tr.css('th')).lower()
                value   = self.get_text(tr.css('td'))
                
                if key == 'prix en ฿':
                    ads_item['price_btc'] = value
                elif key == 'catégorie':
                    ads_item['category'] = value
                elif key == 'vendeur':
                    value = tr.xpath(".//a/@href").extract_first()
                    value = re.search("/account/(.*)/$", value).group(1)
                    ads_item['vendor_username'] = value
                elif key == 'escrow':
                    ads_item['escrow'] = value
                elif key == 'description':
                    ads_item['description'] = value
                elif key in ['prix en €']:
                    ads_item['price_eur'] = value
                else:
                    self.logger.warning("Found a new piece of product information, '%s', with value '%s' at %s" % (key, value, response.url))

            yield ads_item

            images_url = response.css('.card-img-top a img::attr(src)').extract()

            for url in images_url:
                if url:
                    ads_image = items.AdsImage(image_urls = [])
                    ads_image['image_urls'].append(self.make_request('image', url=url))
                    ads_image['ads_id'] = offer_id
                    yield ads_image

        except Exception as error:
            self.logger.warning("Failed to yield ads at %s because '%s'" % (response.url, error))

    def parse_vendor(self, response):
        try:
            user                    = items.User()
            user['relativeurl']     = self.get_relative_url(response.url)
            user['fullurl']         = response.url
            user['profile']         = self.get_text(response.css('.mb-3 p.card-text'))
            user['username']        = re.search(r'/account/([\w-]+)/', response.url).group(1)

            if not response.xpath('.//div[@class="card-body"]/a[contains(text(), "au shop")]'):
                user['is_buyer']    = True
            else:
                user['is_buyer']    = False

            pgp = self.get_text(response.css('div.card-body pre'))
            if 'PGP' in pgp:
                user['public_pgp_key'] = pgp

            trs = response.css("table.m-0 tr")

            for tr in trs:
                key     = self.get_text(tr.css('th')).lower()
                value   = self.get_text(tr.css('td'))

                if value is not '':
                    if key == 'likes':
                        user['positive_feedback'] = int(value)
                    elif key == 'unlikes':
                        user['negative_feedback']  = int(value)
                    elif key == 'moyenne':
                        user['average_rating_percent'] = float(re.search(r'([\d,]+)%', value).group(1).replace(',','.'))
                    elif key == 'inscr.':
                        user['join_date'] = self.parse_datetime(value)
                    elif key == 'dern.co.':
                        user['last_active'] = self.parse_datetime(value)
                    elif key == 'identité fdw':
                        user['forum_username'] = value
                    elif key == 'e-mail':
                        user['email'] = value
                    elif key == 'irc':
                        user['irc'] = value
                    elif key == 'ricochet':
                        user['ricochet'] = value
                    elif key == 'bitmessage':
                        user['bitmessage'] = value
                    elif key == 'btc':
                        user['btc_address'] = value
                    elif value == '' or key == 'jid':
                        pass
                    else:
                        self.logger.warning("Found a new piece of user information, '%s', with value '%s' at %s" % (key, value, response.url))
            yield user

        except Exception as error:
            self.logger.warning("Failed to yield user at %s because '%s'" % (response.url, error))

    def parse_feedback(self, response):
        try:
            username = re.search('/feedback_list/([\w-]+)/', response.url).group(1)

            user_rating                 = items.UserRating()
            user_rating['username']     = username

            trs = response.css('table.m-0 tr')

            for tr in trs:
                user_rating['submitted_by']     = self.get_text(tr.css('td:nth-child(2)'))
                user_rating['submitted_on']     = self.parse_datetime(self.get_text(tr.css('td:nth-child(3)')))
                user_rating['comment']          = self.get_text(tr.css('td:last-child'))

            
            if user_rating['comment'] != 'Pas de feedbacks pour le moment':
                yield user_rating

        except Exception as error:
            self.logger.warning("Failed to yield user feedback at %s because '%s'" % (response.url, error))
