# coding=utf-8

from scrapyprj.spiders.MarketSpiderV2 import MarketSpiderV2
from scrapy.http import FormRequest, Request
import re
import scrapyprj.items.market_items as items

# For http 302 handling
from scrapy.utils.python import to_native_str
from six.moves.urllib.parse import urljoin


class TochkaPointMarketSpider(MarketSpiderV2):
    name = "tochkapoint_market"
    custom_settings = {
        'IMAGES_STORE': './files/img/tochkapointmarket',
        'RANDOMIZE_DOWNLOAD_DELAY': True,
        'HTTPERROR_ALLOW_ALL': True,
        'RETRY_ENABLED': True,
        'RETRY_TIMES': 5,
        'MAX_LOGIN_RETRY': 10
    }
    handle_httpstatus_list = [302]

    def __init__(self, *args, **kwargs):
        super(TochkaPointMarketSpider, self).__init__(*args, **kwargs)
        self.set_max_concurrent_request(1)      # Scrapy config
        self.set_download_delay(10)             # Scrapy config
        self.set_max_queue_transfer_chunk(1)    # Custom Queue system
        self.statsinterval = 60            # Custom Queue system
        # Marketspider2 settings.
        self.recursive_flag = False  # Same as self.islogged-flag in ForumSpiderV3.
        self.report_status = True
        self.report_other_hostnames = False
        # Custom for this spider.
        self.max_captcha_attempts = 10
        self.captcha_trial = 0
        self.logintrial = 0

    def start_requests(self):
        yield self.make_request(reqtype='index', dont_filter=True, shared=False)

    def make_request(self, reqtype='regular', **kwargs):
        if 'url' in kwargs:
            kwargs['url'] = self.make_url(kwargs['url'])

        if reqtype == 'index':
            req = Request(self.make_url('index'), headers=self.tor_browser)
            req.meta['shared'] = False
            req.dont_filter = True
        elif reqtype == 'loginpage':
            req = Request(self.make_url('login'), headers=self.tor_browser)
            req.dont_filter = True
            req.meta['shared'] = False
        elif reqtype == 'dologin':
            req = self.request_from_login_page(kwargs['response'])
            req.dont_filter = True
            req.meta['shared'] = False
        elif reqtype == 'captcha_img':
            req = Request(kwargs['url'], headers=self.tor_browser)
            req.dont_filter = True
            req.meta['shared'] = False
        elif reqtype in ['image']:
            req = Request(self.make_url(kwargs['url']), headers=self.tor_browser)
            req.meta['shared'] = True
        elif reqtype == 'regular':
            req = Request(self.make_url(kwargs['url']), headers=self.tor_browser)

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

        # Some default'ish options.
        req.meta['reqtype'] = reqtype
        req.meta['proxy'] = self.proxy
        req.meta['slot'] = self.proxy

        # return req
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
            # DDoS and login handling block.
            req_once_logged = response.meta['req_once_logged'] if 'req_once_logged' in response.meta else response.request
            if self.is_login_page(response) is True:
                self.logger.warning("%s: On login page. Proceeding to log in." % self.login['username'])
                self.logintrial += 1
                if self.logintrial > self.settings['MAX_LOGIN_RETRY']:
                    self.wait_for_input("Too many login failed", req_once_logged)
                    self.logintrial = 0
                    return
                yield self.make_request(reqtype='dologin', response=response, dont_filter=True, req_once_logged=req_once_logged)
            elif self.islogged(response) is False:
                self.logger.warning("Going to login page.")
                self.captcha_trial = 0
                self.logintrial = 0
                yield self.make_request(reqtype='loginpage', req_once_logged=req_once_logged, dont_filter=True)
            else:
                self.logger.warning('DDoS/Login-block: This is not supposed to happen. HTML %s' % response.body)

        else:
            self.recursive_flag = True
            self.captcha_trial = 0
            self.logintrial = 0
            if response.meta['reqtype'] == 'dologin':
                self.logger.info("Succesfully logged in as %s! Setting parsing flag." % (self.login['username']))

            if self.is_listing_page(response):
                parser = self.parse_listing
            elif self.is_vendor_page(response):
                parser = self.parse_vendor
            elif self.is_buyer_page(response):
                parser = self.parse_buyer
            if parser is not None:
                for x in parser(response):
                    yield x

    # ############## FLAGS #################
    def islogged(self, response):
        logged_in = response.xpath(".//form//i[contains(@class,'sign out')]")
        logged_in_auth = '404 page not found' in response.body and response.url.endswith("/auth/login") # Requesting login while logged in gives this.
        if logged_in:
            return True
        elif logged_in_auth == True:
            return True
        else:
            return False

    def is_login_page(self, response):
        input_username = response.xpath(".//form//input[@name='username']")
        input_password = response.xpath(".//form//input[@name='passphrase']")
        if input_username and input_password:
            return True
        else:
            return False

    def is_vendor_page(self, response):
        vendor_tag = response.xpath(
            ".//div[@class='user info']//div[@class='header']/div[text()[contains(.,'Vendor')]]")
        if vendor_tag and ("/user/" in response.url):
            if self.is_vendor_about(response):
                return True
            elif self.is_vendor_contact(response):
                return True
            elif self.is_vendor_statistics(response):
                return True
            elif self.is_vendor_trusted(response):
                return True
            else:
                return False
        else:
            return False

    def is_vendor_about(self, response):
        if "?section=info" in response.url:
            return True
        elif "?section=info" in response.xpath("//div[@class='ui horizontal fluid menu tiny secondary']/a[@class='item active']/@href").extract_first(default=""):
            return True
        else:
            return False

    def is_vendor_contact(self, response):
        if "?section=contacts" in response.url:
            return True
        elif "?section=contacts" in response.xpath("//div[@class='ui horizontal fluid menu tiny secondary']/a[@class='item active']/@href").extract_first(default=""):
            return True
        else:
            return False

    def is_vendor_statistics(self, response):
        if "?section=vendor_statistics" in response.url:
            return True
        elif "?section=vendor_statistics" in response.xpath("//div[@class='ui horizontal fluid menu tiny secondary']/a[@class='item active']/@href").extract_first(default=""):
            return True
        else:
            return False

    def is_vendor_trusted(self, response):
        if "?section=trusted_seller" in response.url:
            return True
        elif "?section=trusted_seller" in response.xpath("//div[@class='ui horizontal fluid menu tiny secondary']/a[@class='item active']/@href").extract_first(default=""):
            return True
        else:
            return False

    def is_listing_page(self, response):
        if "/item/" in response.url:
            offer_id = re.search(r"/item/([^/]+)", response.url, re.M | re.I)
            offer_id = offer_id.group(1) if offer_id else None
            if offer_id and response.url.endswith(offer_id):
                return True
            else:
                return False
        else:
            return False

    def is_buyer_page(self, response):
        buyer_tag = response.xpath(
            ".//div[@class='user info']//div[@class='header']/div[text()[contains(.,'Buyer')]]")
        if buyer_tag and ("/user/" in response.url) and ("?section=" not in response.url):
            return True
        else:
            return False

    # ############ REQUEST CREATION ################
    def request_from_login_page(self, response):
        params = {
            "username": self.login["username"],
            "passphrase": self.login["password"],
            "captcha_id": response.xpath(".//form//input[@name='captcha_id']/@value").extract_first(),
            "captcha": response.xpath(".//form//input[@name='captcha']/@value").extract_first()
        }
        captcha_src = response.xpath(".//form//img[contains(@class,'captcha')]/@src").extract_first()
        req = FormRequest.from_response(response, formdata=params, headers=self.tor_browser, dont_filter=True)
        req.meta['captcha'] = {
            'request': self.make_request(reqtype="captcha_img", url=captcha_src, headers=self.tor_browser, dont_filter=True, shared=False),
            'name': 'captcha'
        }
        return req

    def get_shipping_options(self, response):
        options_list = []
        out_of_stock = response.xpath(".//div[@class='ui segment']/h3[contains(text(),'Purchase')]/../div[contains(text(),'Out of stock')]")
        if out_of_stock:
            return [], []
        options = response.xpath(".//div[@class='ui segment']/h3[contains(text(),'Purchase')]/../a[contains(@href,'/package/')]")
        for option in options:
            book_url        = option.xpath("@href").extract_first(default="")
            package_id      = re.search(r"/package/([^/]+)", book_url, re.M | re.I)
            package_id      = package_id.group(1) if package_id else None
            name            = option.xpath("div[contains(@class,'tiny button')]/text()").extract_first(default="").strip()
            price_str       = option.xpath("div[contains(@class,'tiny price')]/text()").extract_first(default="").strip()
            package_type    = self.get_text(option.xpath("following-sibling::table[@class='ui table'][1]/tbody/tr/td[1]"))
            ships_to        = self.get_text(option.xpath("following-sibling::table[@class='ui table'][1]/tbody/tr/td[2]"))
            ships_from      = self.get_text(option.xpath("following-sibling::table[@class='ui table'][1]/tbody/tr/td[3]"))

            option_dict = {
                "package_id": package_id,
                "name": name,
                "price": price_str,
                "type": package_type,
                "ships_to": ships_to,
                "ships_from": ships_from
                }
            options_list.append(option_dict)
        return options_list

    def get_verification_process(self, response):
        verification_process = []
        process = response.xpath("//div[@class='ui comments']//div[@class='comment']//div[@class='content']")
        if process:
            for content in process:
                proc_dict = {
                    "username": content.xpath(".//a[@class='author']/@href").extract_first(default="").replace("/user/", ""),
                    "date": self.parse_datetime(content.xpath(".//div//span[@class='date']/text()").extract_first(default="").strip()),
                    "text": self.get_text(content.xpath(".//pre"))
                }
                verification_process.append(proc_dict)
        return verification_process

    # ######### PARSERS ###############
    def parse_listing(self, response):
        # The ad.
        ads_item                    = items.Ads()
        ads_item["offer_id"]        = re.search(r"/item/([^/]+)", response.url, re.M | re.I)
        if ads_item["offer_id"]:
            ads_item["offer_id"]    = ads_item["offer_id"].group(1)
        else:
            self.logger.warning("offer_id is None at %s" % response.url)
            return
        ads_item["vendor_username"] = re.search(r"/user/([^/]+)", response.url, re.M | re.I)
        if ads_item["vendor_username"]:
            ads_item["vendor_username"] = ads_item["vendor_username"].group(1)
        ads_item["fullurl"]             = response.url.split(ads_item["offer_id"])[0] + ads_item["offer_id"]
        ads_item["relativeurl"]         = self.get_relative_url(ads_item["fullurl"])
        ads_item["title"]               = "".join(response.xpath(".//div[@class='ui segment inverted t-item-image secondary']/h3/text()").extract()).strip()
        ads_item["description"]         = self.get_text(response.xpath(".//div[@class='ui segment']/h3[contains(text(),'About')]/following-sibling::div"))
        ads_item["shipping_options"]    = self.get_shipping_options(response)
        ads_item["product_rating"] = response.xpath(".//div[@class='ui segment inverted t-item-image secondary']/h3//i[@class='icon thumbs up']/following-sibling::span/text()").extract_first(default="").strip()
        yield ads_item
        # The images.
        image_urls = response.xpath(".//div[@class='ui segment inverted t-item-image secondary']/img/@src").extract()
        if len(image_urls) > 0:
            img_item = items.AdsImage(image_urls=[])
            for img_url in image_urls:
                img_item['image_urls'].append(self.make_request(reqtype='image', url=img_url))
            img_item['ads_id'] = ads_item['offer_id']
            yield img_item
        # The reviews.
        feedbacks = response.xpath(".//div[@class='ui segment']/h3[contains(text(),'Reviews')]/following-sibling::div[@class='ui comments']/div[@class='comment']")
        if feedbacks:
            for feedback in feedbacks:
                rating                        = items.ProductRating()
                rating["ads_id"]              = ads_item["offer_id"]
                rating["submitted_by"]        = feedback.xpath(".//a[@class='author']/text()").extract_first(default="").strip().replace("@", "")
                rating["submitted_on_string"] = feedback.xpath(".//span[@class='date']/text()").extract_first(default="").strip()
                rating["submitted_on"]        = self.parse_datetime(rating["submitted_on_string"])
                rating["comment"]             = self.get_text(feedback.xpath(".//pre[@class='text']"))
                rating["rating"]              = feedback.xpath(".//i[@class='icon thumbs up']/following-sibling::span/text()").extract_first(default="").strip()
                yield rating

    def get_vendor_main_info(self, response):
        try:
            vendor = items.User()
            vendor["username"]          = self.get_text(response.xpath(".//div[@class='user info']//div[@class='content']//a[@class='header']"))
            vendor["username"]          = vendor["username"].replace("@", "")
            vendor["relativeurl"]       = response.xpath(".//div[@class='user info']//div[@class='content']//a[@class='header']/@href").extract_first(default="")
            vendor["fullurl"]           = self.make_url(vendor["relativeurl"])
            vendor["last_active"]       = response.xpath(".//div[@class='user info']//div[@class='meta']//span[contains(text(),'Last seen')]/text()").extract_first(default="").strip()
            vendor["last_active"]       = vendor["last_active"].replace("Last seen", "").strip()
            vendor["last_active"]       = self.parse_datetime(vendor["last_active"])
            vendor["join_date"]         = response.xpath(".//div[@class='user info']//div[@class='meta']//span[contains(text(),'Registered')]/text()").extract_first(default="").strip()
            vendor["join_date"]         = vendor["join_date"].replace("Registered", "").strip()
            vendor["join_date"]         = self.parse_datetime(vendor["join_date"]).date()
            vendor["level"]             = response.xpath(".//div[@class='user info']//div[@class='header']/div[contains(text(),'Level:')]/text()").extract_first(default="").strip()
            vendor["level"]             = vendor["level"].replace("Level:", "").strip()
            vendor["trusted_seller"]    = response.xpath(".//div[@class='user info']//div[@class='header']/div[text()[contains(.,'Trusted Vendor')]]")
            vendor["trusted_seller"]    = True if vendor["trusted_seller"] else False
            vendor["average_rating"]    = response.xpath(".//div[@class='user info']//div[@class='extra content']//i[@class='icon thumbs up']/following-sibling::span/text()").extract_first(default="").strip()
            vendor["feedback_received"] = self.get_text(response.xpath(".//div[@class='ui vertical menu tiny basic fluid secondary']/a[contains(@href,'/reviews')]/span"))
            vendor["warnings_number"]   = self.get_text(response.xpath(".//div[@class='ui vertical menu tiny basic fluid secondary']/a[contains(@href,'/warnings')]/span"))
            vendor["has_warning"]       = True if (vendor["warnings_number"] != "") and (vendor["warnings_number"] != "0") else False
            vendor["member_class"]      = response.xpath(".//div[@class='user info']//div[@class='header']/div[contains(text(),'Vendor')]/text()").extract_first(default="").strip()
            vendor["ship_from"]         = response.xpath(".//div[@class='user info']//a[@class='header']/i[contains(@class,'flag')]/@class").extract_first(default="")
            vendor["ship_from"]         = vendor["ship_from"].replace("flag", "").strip()
            return vendor
        except Exception as error:
            self.logger.warning("Couldn't yield vendor at %s (Error: %s)" % (response.url, error))

    def parse_vendor(self, response):
        vendor = self.get_vendor_main_info(response)
        if self.is_vendor_about(response):
            vendor["profile"] = self.get_text(response.xpath(".//div[@class='segment ui']/h3[contains(text(),'About')]/following-sibling::div[@class='ui container']"))
        elif self.is_vendor_contact(response):
            vendor['email'] = response.xpath(".//div[@class='ui form segment contacts']//div[@class='field']/label[contains(text(),'Email')]/following-sibling::input/@value").extract_first()
            vendor['public_pgp_key'] = self.get_text(response.xpath(".//div[@class='ui form segment contacts']//div[@class='field']/label[contains(text(),'PGP')]/following-sibling::pre"))
        elif self.is_vendor_statistics(response):
            vendor["successful_transactions"] = response.xpath(".//div[@class='ui statistics']//div[contains(@class,'statistic')]/div[contains(text(),'Transactions')]/..//span/text()").extract_first(default="").strip()
        elif self.is_vendor_trusted(response):
            vendor["verification_process"] = self.get_verification_process(response)
        else:
            self.logger.warning("Not in [About, Contact, Statistics, Trusted Vendor], so skip parsing: %s" % response.url)
            return
        yield vendor

    def parse_buyer(self, response):
        try:
            buyer = items.User()
            buyer["is_buyer"]          = True
            buyer["username"]          = self.get_text(response.xpath(".//div[@class='user info']//div[@class='content']//a[@class='header']"))
            buyer["username"]          = buyer["username"].replace("@", "")
            buyer["relativeurl"]       = response.xpath(".//div[@class='user info']//div[@class='content']//a[@class='header']/@href").extract_first(default="")
            buyer["fullurl"]           = self.make_url(buyer["relativeurl"])
            buyer["last_active"]       = response.xpath(".//div[@class='user info']//div[@class='meta']//span[contains(text(),'Last seen')]/text()").extract_first(default="").strip()
            buyer["last_active"]       = buyer["last_active"].replace("Last seen", "").strip()
            buyer["last_active"]       = self.parse_datetime(buyer["last_active"])
            buyer["join_date"]         = response.xpath(".//div[@class='user info']//div[@class='meta']//span[contains(text(),'Registered')]/text()").extract_first(default="").strip()
            buyer["join_date"]         = buyer["join_date"].replace("Registered", "").strip()
            buyer["join_date"]         = self.parse_datetime(buyer["join_date"]).date()
            buyer["buyer_profile"]     = self.get_text(response.xpath(".//div[@class='segment ui']/h3[contains(text(),'About')]/following-sibling::div[@class='ui container']"))
            buyer["buyer_country"]     = response.xpath(".//div[@class='user info']//a[@class='header']/i[contains(@class,'flag')]/@class").extract_first(default="")
            buyer["buyer_country"]     = buyer["buyer_country"].replace("flag", "").strip()
            yield buyer
        except Exception as error:
            self.logger.warning("Couldn't yield buyer at %s (Error: %s)" % (response.url, error))
