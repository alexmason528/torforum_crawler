# coding=utf-8

from scrapyprj.spiders.MarketSpiderV2 import MarketSpiderV2
from scrapy.http import FormRequest, Request
import re
import scrapyprj.items.market_items as items
from urlparse import urljoin
from scrapy.shell import inspect_response

# For http 302 handling
from scrapy.utils.python import to_native_str
from six.moves.urllib.parse import urljoin


    # average_rating = scrapy.Field()
    # payment = scrapy.Field()
    # price_btc = scrapy.Field()
    # refund_policy = scrapy.Field()
    # tags = scrapy.Field()
    #rating_type = scrapy.Field()


class ApollonMarketSpider(MarketSpiderV2):
    name = "apollon_market"
    custom_settings = {
        'IMAGES_STORE': './files/img/apollonmarket',
        'RANDOMIZE_DOWNLOAD_DELAY': True,
        'HTTPERROR_ALLOW_ALL': True,
        'RETRY_ENABLED': True,
        'RETRY_TIMES': 5,
        'MAX_LOGIN_RETRY': 10,
    }
    handle_httpstatus_list = [404, 302]

    def __init__(self, *args, **kwargs):
        super(ApollonMarketSpider, self).__init__(*args, **kwargs)
        self.set_max_concurrent_request(1)      # Scrapy config
        self.set_download_delay(10)             # Scrapy config
        self.set_max_queue_transfer_chunk(1)    # Custom Queue system
        self.statsinterval = 60            # Custom Queue system
        # Marketspider2 settings.
        self.recursive_flag = False  # Same as self.islogged-flag in ForumSpiderV3.
        self.report_status = True
        self.report_other_hostnames = False
        # Custom for this spider.
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
            req.dont_filter = False
        elif reqtype == 'loginpage':
            req = Request(self.make_url('login'), headers=self.tor_browser)
            req.meta['shared'] = False
        elif reqtype == 'dologin':
            req = self.request_from_login_page(kwargs['response'])
            req.meta['shared'] = False
        elif reqtype == 'captcha_img':
            req = Request(kwargs['url'], headers=self.tor_browser)
            req.dont_filter = True
            req.meta['shared'] = False
        elif reqtype in ['image']:
            req = Request(self.make_url(kwargs['url']), headers=self.tor_browser)
            req.meta['shared'] = False
        elif reqtype == 'tab':
            req = Request(self.make_url(kwargs['url']), headers=self.tor_browser)
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

        return req
        #return self.set_priority(req)

    def parse_response(self, response):
        parser = None
        if response.status >= 300 and response.status < 400:
            self.recursive_flag = False
            location        = to_native_str(response.headers['location'].decode('latin1'))
            request         = response.request
            redirected_url  = urljoin(request.url, location)
            req             = self.make_request(reqtype = 'regular', url = redirected_url, dont_filter = True, shared = False)
            if response.meta['reqtype']:
                req.meta['reqtype'] = response.meta['reqtype']
            req.meta['req_once_logged'] = response.meta['req_once_logged'] if 'req_once_logged' in response.meta else response.request
            req.priority                = 50
            self.logger.warning("%s: Being redirected from %s to %s" % (self.login['username'], request.url, redirected_url))
            yield req        
        elif self.islogged(response) is False:
            self.recursive_flag = False
            # DDoS and login handling block.
            req_once_logged = response.meta['req_once_logged'] if 'req_once_logged' in response.meta else response.request
            if self.is_login_page(response) is True:
                self.logger.warning("On login page. Proceeding to log in.")
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
            if parser is not None:
                for x in parser(response):
                    yield x

    # ############## FLAGS #################
    def islogged(self, response):
        logged_in = response.xpath(".//a[@href='logout.php']")
        if logged_in:
            return True
        else:
            return False

    def is_login_page(self, response):
        input_username = response.xpath(".//form//input[@name='l_username']")
        input_password = response.xpath(".//form//input[@name='l_password']")
        if input_username and input_password:
            return True
        else:
            return False

    def is_vendor_page(self, response):
        if "user.php?u_id=" in response.url:
            return True
        else:
            return False

    def is_vendor_tab_page(slef, response):
        if ("user.php?u_id=" in response.url) and ("&tab=" in response.url):
            return True
        else:
            return False

    def is_listing_page(self, response):
        if "listing.php?ls_id=" in response.url:
            return True
        else:
            return False

    def is_listing_tab_page(slef, response):
        if ("listing.php?ls_id=" in response.url) and ("&tab=" in response.url):
            return True
        else:
            return False

    # ############ REQUEST CREATION ################
    def request_from_login_page(self, response):
        params = {
            "l_username": self.login["username"],
            "l_password": self.login["password"],
        }
        captcha_src = response.xpath(".//form//img[@name='captcha_code']/@src").extract_first()
        captcha_src = urljoin(self.spider_settings['endpoint'], captcha_src)
        req = FormRequest.from_response(response, formdata=params, headers=self.tor_browser, dont_filter=True)
        req.meta['captcha'] = {
            'request': self.make_request(reqtype="captcha_img", url=captcha_src, dont_filter=True, shared=False),
            'name': 'captcha_code'
        }
        return req

    # def requests_from_listing_page(self, response):
    #     for url in response.xpath("//ul[@class='nav nav-tabs']//a[contains(@href,'&tab=')]/@href").extract():
    #         url = urljoin(self.spider_settings['endpoint'], url)
    #         if "user.php" not in url:
    #             self.logger.warning("Skip user link (%s) on product page at %s" % (url, response.url))
    #             continue
    #         yield self.make_request(reqtype='tab', url=url, dont_filter=True, shared=True)

    def get_shipping_options(self, response):
        options_list = []
        for option in response.xpath("//select[@name='p_psg']/option"):
            # e.g.
            #     (100Pcs) DHL - 7 Days - 63.00 USD
            #     FREE - 1 Day - 0.00 USD
            option_str = self.get_text(option)
            try:
                option_dict = {
                    "type": option_str.split("-")[0].strip(),
                    "period": option_str.split("-")[1].strip(),
                    "price": option_str.split("-")[2].strip()
                }
                options_list.append(option_dict)
            except IndexError as e:
                self.logger.warning("IndexError with %s at %s: %s" % (option_str, response.url, str(e)))
        return options_list

    # ######### PARSERS ###############
    def parse_listing(self, response):
        try:
            ads_item = items.Ads()
            ads_item["offer_id"]            = re.search(r"ls_id=(\d+)", response.url, re.M | re.I).group(1)
            ads_item["vendor_username"]     = self.get_text(response.xpath("//small/a[contains(@href,'user.php?u_id=')]"))
            ads_item["vendor_username"]     = ads_item["vendor_username"].split("(")[0].strip()
            ads_item["fullurl"]             = response.url.split("&")[0]
            ads_item["relativeurl"]         = self.get_relative_url(ads_item["fullurl"])
            ads_item["title"]               = response.xpath(".//div[@class='col-sm-12']/a[contains(@href, 'ls_id')]/text()").extract_first()
            ads_item["ships_to"]            = self.get_text(response.xpath("//small//b[contains(text(),'Ship To :')]/ancestor::small")).replace("Ship To :", "").strip()
            if ads_item["ships_to"] == "":
                #self.logger.warning("Fallback to other shipping to field at %s." % response.url)
                ads_item["ships_to"]        = self.get_text(response.xpath("//small//b[contains(text(),'Ship To :')]/ancestor::small/following-sibling::small[1]"))
            ads_item["ships_from"]          = self.get_text(response.xpath("//small//b[contains(text(),'Origin Country :')]/ancestor::small")).replace("Origin Country :", "").strip()
            ads_item["ads_class"]           = self.get_text(response.xpath("//small//b[contains(text(),'Product class :')]/ancestor::small")).replace("Product class :", "").strip()
            ads_item["quantity"]            = self.get_text(response.xpath("//small//b[contains(text(),'Quantity :')]/ancestor::small")).replace("Quantity :", "").strip()

            accepted_currencies = []
            sale_price = self.get_text(response.xpath("//form//span[contains(text(),'Sale Price :')]")).replace("Sale Price :", "").strip()
            if "USD" in sale_price:
                ads_item["price_usd"] = re.search(r"([\d\.]+)\s*USD", sale_price, re.M | re.I)
                ads_item["price_usd"] = ads_item["price_usd"].group(1) if ads_item["price_usd"] else None
            if "BTC" in sale_price:
                ads_item["price_btc"] = re.search(r"([\d\.]+)\s*BTC", sale_price, re.M | re.I)
                ads_item["price_btc"] = ads_item["price_btc"].group(1) if ads_item["price_btc"] else None
                accepted_currencies.append("BTC")
            ads_item["accepted_currencies"] = ",".join(accepted_currencies)
            ads_item["shipping_options"]    = self.get_shipping_options(response)

            # new fields
            ads_item["escrow"]  = self.get_text(response.xpath("//small//b[contains(text(),'Payment :')]/ancestor::small")).replace("Payment :", "").strip()
            active_tab          = self.get_text(response.xpath("//ul[@class='nav nav-tabs']/li[@class='active']/a"))

            if "Product Description" in active_tab:
                ads_item['description'] = self.get_text(response.xpath("//div[@class='tab-content']"))
            elif "Refund Policy" in active_tab:
                ads_item['refund_policy'] = self.get_text(response.xpath("//div[@class='tab-content']"))
            elif "Product Tags" in active_tab:
                pass
            elif "Feedback" in active_tab:
                feedbacks = response.xpath("//div[@class='tab-content']//table/tbody/tr")
                if feedbacks:
                    for feedback in feedbacks:
                        rating                          = items.ProductRating()
                        rating["ads_id"]                = ads_item["offer_id"]
                        rating["submitted_by"]          = self.get_text(feedback.xpath("td[3]/small"))
                        rating["submitted_on_string"]   = self.get_text(feedback.xpath("td[5]/small")).replace("View Item", "").strip()
                        rating["submitted_on"]          = self.parse_datetime(rating["submitted_on_string"])
                        rating["comment"]               = self.get_text(feedback.xpath("td[2]/small"))
                        rating["price_usd"]             = self.get_text(feedback.xpath("td[4]/small"))
                        # new fields
                        score = self.get_text(feedback.xpath("td[1]"))
                        if score == "\xe2\x98\x91":
                            rating["rating"] = "Positive"
                        elif score == "\xe2\x98\x92":
                            rating["rating"] = "Negative"
                        elif score == "\xe2\x98\x90":
                            rating["rating"] = "Neutral"
                        else:
                            self.logger.warning("Unknown rating type '%s' at %s" % (rating["rating"], response.url))
                        yield rating
            else:
                self.logger.warning("Unknown tab: %s at %s" % (active_tab, response.url))
            yield ads_item
        except Exception as error:
            self.logger.warning("Couldn't yield Ad (Error %s) at %s." % (error, response.url))

        if self.is_listing_tab_page(response) is False:
            #     self.requests_from_listing_page(response)
            image_urls = response.xpath(
                "//img[@class='pull-left']/@src").extract()
            if len(image_urls) > 0:
                img_item = items.AdsImage(image_urls=[])
                for img_url in image_urls:
                    # e.g. uploads/9bc5f18d5667081890e8972def13da2f_100_100.png
                    #      -> uploads/9bc5f18d5667081890e8972def13da2f.png
                    img_url = re.sub(r"_\d+_\d+\.", ".", img_url)
                    img_item['image_urls'].append(self.make_request(reqtype='image', url=img_url))
                img_item['ads_id'] = ads_item['offer_id']
                yield img_item

    def parse_vendor(self, response):
        username = re.search(r"u_id=([^&]+)", response.url, re.M | re.I)
        username = username.group(1) if username else None
        if username not in self.spider_settings['logins']:
            vendor = items.User()
            vendor["username"]                         = username
            vendor["fullurl"]                          = response.url.split("&")[0]
            vendor["relativeurl"]                      = self.get_relative_url(vendor["fullurl"])
            vendor["last_active"]                      = self.get_text(response.xpath("//small//b[contains(text(),'Last Login :')]/ancestor::small")).replace("Last Login :", "").strip()
            vendor["last_active"]                      = self.parse_datetime(vendor["last_active"]).date()
            vendor["join_date"]                        = self.get_text(response.xpath("//small//b[contains(text(),'Member since :')]/ancestor::small")).replace("Member since :", "").strip()
            vendor["join_date"]                        = self.parse_datetime(vendor["join_date"]).date()
            vendor["successful_transactions"]          = self.get_text(response.xpath("//small//b[contains(text(),'Sales :')]/ancestor::small")).replace("Sales :", "").strip()
            vendor["successful_transactions_as_buyer"] = self.get_text(response.xpath("//small//b[contains(text(),'Orders :')]/ancestor::small")).replace("Orders :", "").strip()
            vendor["average_rating_percent"]           = self.get_text(response.xpath("//small//b[contains(text(),'Positive Feedback :')]/ancestor::small")).replace("Positive Feedback :", "").strip()
            vendor["average_rating_percent"]           = vendor["average_rating_percent"].replace("(", "")
            vendor["average_rating_percent"]           = vendor["average_rating_percent"].replace(")", "")
            vendor["trusted_seller"]                   = response.xpath("//small//b[contains(text(),'Seller Trusted :')]/ancestor::small//img/@src").extract_first(default="")
            vendor["trusted_seller"]                   = True if "yes_trusted" in vendor["trusted_seller"] else False
            vendor["verified"]                         = response.xpath("//small//b[contains(text(),'Seller Verified :')]/ancestor::small//img/@src").extract_first(default="")
            vendor["verified"]                         = True if "yes_verified" in vendor["verified"] else False
            fe                                         = self.get_text(response.xpath("//small//b[contains(text(),'FE :')]/ancestor::small")).replace("FE :", "").strip()
            vendor["fe_enabled"]                       = False if fe.lower() == "deny" else True

            vendor["badges"] = []
            badges = response.xpath("//small/span[@class='badge']")
            for badge in badges:
                badge = self.get_text(badge)
                if "Seller Level" in badge:
                    vendor["level"] = badge.replace("Seller Level", "").strip()
                elif "Trust Level" in badge:
                    vendor["trust_level"] = badge.replace("Trust Level", "").strip()
                else:
                    self.logger.warning("New badge: '%s' at %s" % (badge, response.url))
                vendor["badges"].append(badge)

            vendor["disputes"]          = self.get_text(response.xpath("//small//b[contains(text(),'Disputes :')]/ancestor::small")).replace("Disputes :", "").strip()
            vendor["positive_feedback"] = self.get_text(response.xpath("//div/button/b[contains(text(),'Positive :')]")).replace("Positive :", "").strip()
            vendor["neutral_feedback"]  = self.get_text(response.xpath("//div/button/b[contains(text(),'Neutral :')]")).replace("Neutral :", "").strip()
            vendor["negative_feedback"] = self.get_text(response.xpath("//div/button/b[contains(text(),'Negative :')]")).replace("Negative :", "").strip()

            active_tab = self.get_text(response.xpath("//ul[@class='nav nav-tabs']/li[@class='active']/a"))
            if "Profile" in active_tab:
                vendor["profile"] = self.get_text(response.xpath("//div[@class='tab-content']//i"))
                # new fields
                vendor["icq"]       = self.get_text(response.xpath("//div[@class='tab-content']//span/b[contains(text(),'ICQ :')]/ancestor::span")).replace("ICQ :", "").strip()
                vendor["jabber"]    = self.get_text(response.xpath("//div[@class='tab-content']//span/b[contains(text(),'Jabber :')]/ancestor::span")).replace("Jabber :", "").strip()
                vendor["email"]     = self.get_text(response.xpath("//div[@class='tab-content']//span/b[contains(text(),'E-Mail :')]/ancestor::span")).replace("E-Mail :", "").strip()
                vendor["website"]   = self.get_text(response.xpath("//div[@class='tab-content']//span/b[contains(text(),'My WebSite :')]/ancestor::span")).replace("My WebSite :", "").strip()
            elif "PGP Public Key" in active_tab:
                vendor["public_pgp_key"] = self.get_text(response.xpath("//div[@class='tab-content']//pre"))
            elif "Feedback" in active_tab:
                pass
            else:
                self.logger.warning("Unknown tab: %s at %s" % (active_tab, response.url))
            yield vendor
