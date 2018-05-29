# coding=utf-8

from scrapyprj.spiders.MarketSpiderV2 import MarketSpiderV2
from scrapy.http import FormRequest, Request
import re
import scrapyprj.items.market_items as items
from scrapy.shell import inspect_response
# Used for demoing 302-handling.
from scrapy.utils.python import to_native_str
from six.moves.urllib.parse import urljoin


class RaptureMarketSpider(MarketSpiderV2):
    name = "rapture_market"
    custom_settings = {
        'IMAGES_STORE': './files/img/rapturemarket',
        'RANDOMIZE_DOWNLOAD_DELAY': True,
        'HTTPERROR_ALLOW_ALL': True,
        'RETRY_ENABLED': True,
        'RETRY_TIMES': 5,
        'MAX_LOGIN_RETRY': 10
        }
    handle_httpstatus_list = [302]

    def __init__(self, *args, **kwargs):
        super(RaptureMarketSpider, self).__init__(*args, **kwargs)
        self.set_max_concurrent_request(1)      # Scrapy config
        self.set_download_delay(10)             # Scrapy config
        self.set_max_queue_transfer_chunk(1)    # Custom Queue system
        self.statsinterval = 60            # Custom Queue system
        # Marketspider2 settings.
        self.recursive_flag = False  # Same as self.islogged-flag in ForumSpiderV3.
        self.report_status = True
        self.report_other_hostnames = False
        # Custom for this spider.
        self.max_captcha_attempts = 50
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
            req.meta['shared'] = True

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
                yield self.make_request(reqtype='dologin', response=response, dont_filter=True, req_once_logged=req_once_logged, shared = False)
            elif self.islogged(response) is False:
                self.logger.warning("Going to login page.")
                self.captcha_trial = 0
                self.logintrial = 0
                yield self.make_request(reqtype='loginpage', req_once_logged=req_once_logged, dont_filter=True, shared = False)
            else:
                self.logger.warning('DDoS/Login-block: This is not supposed to happen. HTML %s' % response.body)

        else:
            self.recursive_flag = True
            self.captcha_trial = 0
            self.logintrial = 0
            if response.meta['reqtype'] == 'dologin':
                self.logger.info("Succesfully logged in as %s! Setting parsing flag and returning to stored request %s" % (self.login['username'], response.meta['req_once_logged']))
                yield response.meta['req_once_logged']

            if self.is_listing_page(response):
                if self.is_multilisting(response):
                    parser = self.requests_from_multilisting
                else:
                    parser = self.parse_listing
            elif self.is_vendor(response):
                parser      = self.parse_vendor
            if parser is not None:
                for x in parser(response):
                    yield x

    # ############## FLAGS #################
    def islogged(self, response):
        logged_in = response.xpath(".//a[contains(@href,'/?logout')]")
        if logged_in:
            return True
        elif '/uploads/' in response.url:
            return True
        else:
            return False

    def is_login_page(self, response):
        login_form = response.xpath(".//div[@class='login_form']/form[@class='loginInput']")
        if len(login_form) == 1:
            return True
        else:
            return False

    def is_vendor(self, response):
        if "?page=profile&user=" in response.url:
            return True
        else:
            return False

    def is_listing_page(self, response):
        if "/?page=listing&lid=" in response.url and 'clid=' not in response.url:
            return True
        else:
            return False

    def is_multilisting(self, response):
        multilisting = self.get_text(response.xpath(".//div[@class='listing_info']//div[@class='listing_right']//span[contains(text(),'Multilisting')]"))
        if multilisting.lower() == "multilisting":
            return True
        else:
            return False

    # ############ REQUEST CREATION ################
    def requests_from_multilisting(self, response):
        """
            e.g. response.url =
                http://ngdek3r3xp3bzkza.onion/?page=listing&lid=cVPk5SIHDy7nO9sY
                http://ngdek3r3xp3bzkza.onion/?page=listing&lid=BY9RZvGfOdvvgECn&clid=o3JdvJhJPjqERZaK
        """
        sublisting_ids = response.xpath(".//form//select[@name='multilistingChild']/option/@value").extract()
        if sublisting_ids:
            for clid in sublisting_ids:
                if clid != "":
                    sublisting_url = self.spider_settings['endpoint'] + "?page=listing&lid=" + clid
                    yield self.make_request(url=sublisting_url, headers=self.tor_browser)

    def request_from_login_page(self, response):
        if response.xpath(".//form/input[@name='captchO']"):
            # first captcha page
            self.logger.warning("Login captcha page.")
            params = {
                "token": response.xpath(".//form/input[@name='token']/@value").extract_first(),
                "username": self.login['username'],
                "captchO": response.xpath(".//form/input[@name='captchO']/@value").extract_first(),
                "submit": response.xpath(".//form/input[@name='submit']/@value").extract_first()
            }
            captcha_src = response.xpath('.//form/a/img/@src').extract_first()
            captcha_src = re.sub(r"^data:image\/[^;]+", "data:application/octet-stream", captcha_src)
            req = FormRequest.from_response(response, formdata=params, headers=self.tor_browser, dont_filter=True)
            req.meta['captcha'] = {
                'request': self.make_request(reqtype="captcha_img", url=captcha_src, headers=self.tor_browser, dont_filter=True, shared=False),
                'name': 'captchO',
                'afterprocess': 'RaptureMarketRemoveFirstLetter'
            }
        else:
            # second password page
            self.logger.warning("Login password page.")
            params = {
                "token": response.xpath(".//form/input[@name='token']/@value").extract_first(),
                "password": self.login['password'],
                "submitAuth": response.xpath(".//form/input[@name='submitAuth']/@value").extract_first()
            }
            req = FormRequest.from_response(response, formdata=params, headers=self.tor_browser, dont_filter=True)
        return req

    def get_shipping_options(self, response):
        options_list = []
        options = response.xpath(".//form//select[@name='shipment']/option/text()").extract()
        for option in options:
            value = re.search(r"(.*) - ([\d\.\s\$]+)", option, re.M | re.I)
            if value:
                option_dict = {
                    'price': value.group(2).strip(),
                    'name': value.group(1).strip()
                    }
                options_list.append(option_dict)
        return options_list

    def get_accepted_currencies(self, response):
        accepted_currencies = response.xpath(".//section[@id='content1']//div[@class='listing_right']//img[contains(@title,' accepted')]/@alt").extract()
        accepted_currencies = ["btc" if x.lower() == "bitcoin" else x for x in accepted_currencies]
        accepted_currencies = ["xmr" if x.lower() == "monero" else x for x in accepted_currencies]
        accepted_currencies = ",".join(accepted_currencies)
        return accepted_currencies

    # ######### PARSERS ###############
    def parse_listing(self, response):
        title       = response.xpath(".//section[@id='content1']//div[@class='listing_right']/span/text()").extract_first(default="").strip()
        username    = response.xpath(".//section[@id='content1']//div[@class='listing_right']//a[@class='greenlink']/text()").extract_first(default="").strip()
        if title == "" and username == "":
            self.logger.warning("Found what is likely an empty page at %s." % response.url)
        else:
            # Try to yield ads.
            try:
                ads_item                    = items.Ads()
                ads_item['title']           = title
                ads_item['vendor_username'] = username
                ads_item['relativeurl']     = self.get_relative_url(response.url)
                ads_item['fullurl']         = response.url
                if 'clid' in response.url:
                    ads_item['offer_id']    = self.get_url_param(response.url, 'clid')                    
                else:
                    ads_item['offer_id']    = self.get_url_param(response.url, 'lid')
                ads_item['category']        = response.xpath(".//section[@id='content1']//div[@class='listing_right']/br/following-sibling::span/text()").extract_first(default="").strip()
                ads_item['ships_from']      = response.xpath(".//section[@id='content1']//div[@class='listing_right']//b[contains(text(),'Shipping From:')]/following-sibling::span/text()").extract_first(default="").strip()
                ads_item['ships_to']        = response.xpath(".//section[@id='content1']//div[@class='listing_right']//b[contains(text(),'Shipping To:')]/following-sibling::span/text()").extract_first(default="").strip()
                ads_item['description']     = self.get_text(response.xpath(".//section[@id='content1']/p"))
                ads_item['escrow']          = self.get_text(response.xpath(".//section[@id='content1']//div[@class='listing_right']/div/span[@style='float:right']/span"))
                ads_item['multisig']        = response.xpath(".//section[@id='content1']//div[@class='listing_right']/div/span[@style='float:right']/img[@alt='Multisig']")
                ads_item['multisig']        = True if ads_item['multisig'] else False
                ads_item['stock']           = self.get_text(response.xpath(".//section[@id='content1']//div[@class='listing_right']/div/span[not(@style='float:right')]/span"))
                ads_item['shipping_options'] = self.get_shipping_options(response)
                ads_item['accepted_currencies'] = self.get_accepted_currencies(response)

                prices_text = self.get_text(response.xpath(".//section[@id='content1']//div[@class='listing_right']/p"))
                price_usd = re.search(r"\$\s*([\d\.]+)", prices_text, re.M | re.I)
                price_btc = re.search(r"([\d\.]+)\s*฿", prices_text, re.M | re.I)
                price_xmr = re.search(r"([\d\.]+)\s*XMR", prices_text, re.M | re. I)

                if price_usd:
                    ads_item["price_usd"] = price_usd.group(1)
                else:
                    self.logger.warning("No price_usd found on %s" % response.url)
                if price_xmr:
                    ads_item["price_xmr"] = price_xmr.group(1)
                if price_btc:
                    ads_item["price_btc"] = price_btc.group(1)
                
                yield ads_item
            except Exception as error:
                self.logger.warning("Couldn't yield ad from %s (Error: %s)" % (response.url, error))
            # Try to yield images.
            try:
                image_urls = response.xpath(".//section[@id='content1']//div[@class='listing_image']/img/@src").extract()
                if len(image_urls) > 0:
                    img_item = items.AdsImage(image_urls=[])
                    for img_url in image_urls:
                        img_item['image_urls'].append(self.make_request(reqtype='image', url=img_url))
                    img_item['ads_id'] = ads_item['offer_id']
                    yield img_item
            except Exception as error:
                self.logger.warning("Couldn't yield ad images from %s (Error: %s)" % (response.url, error))

        # Yield product ratings.
        # Note, that the price is also available in ads. 
        feedbacks = response.xpath(".//section[@id='content2']//div[@class='feedback']")
        if feedbacks:
            for feedback in feedbacks:
                rating                          = items.ProductRating()
                rating["ads_id"]                = ads_item["offer_id"]
                rating["submitted_on_string"]   = feedback.xpath("div[@class='feedback_header']/span/text()").extract_first(default="").strip()
                rating["submitted_on"]          = self.parse_datetime(rating["submitted_on_string"])
                rating['price_usd']         = feedback.xpath("div[@class='feedback_subheader']/div/span/text()[contains(., 'USD')]").extract_first()
                rating['price_usd']         = rating['price_usd'].replace("~", "").replace("USD", "").replace(" ", "")
                rating_star                     = feedback.xpath("div[@class='feedback_subheader']//div[contains(@style,'img/star.png')]/@style").extract_first(default="")
                rating_star                     = re.search(r"width:(\d+)px;height", rating_star, re.M | re.S)
                if rating_star:
                    rating_star                 = float(rating_star.group(1))
                    rating['rating']            = rating_star / 120 * 5
                warning                         = feedback.xpath("div[@class='feedback_subheader']/div/span")
                if warning and len(warning) > 1:
                    rating['warnings']          = self.get_text(warning[0])
                rating["comment"]               = self.get_text(feedback.xpath("p"))
                rating["submitted_by"]          = feedback.xpath("div[@class='feedback_header']//span[@class='feedbackScore']/../text()").extract_first(default="").strip()
                rating["submitter_rating"]      = self.get_text(feedback.xpath("div[@class='feedback_header']//span[@class='feedbackScore']/sup"))
                rating["submitted_by_number_transactions"] = self.get_text(feedback.xpath("div[@class='feedback_header']//span[@class='feedbackScore']/sub"))

                yield rating

    def parse_vendor(self, response):
        vendor_profile = response.xpath(".//section[@id='content1']//span[contains(text(),'Vendor')]/text()").extract_first()
        if vendor_profile and vendor_profile.strip() == "Vendor":
            # Yield vendor.
            try:
                vendor                      = items.User()
                vendor['username']          = response.xpath(".//section[@id='content1']//span[@class='feedbackScore']/../text()").extract_first(default="").strip()
                vendor['relativeurl']       = self.get_relative_url(response.url)
                vendor['fullurl']           = response.url
                vendor['last_active']       = response.xpath(".//section[@id='content1']//label[contains(text(),'Last Logged')]/following-sibling::span/text()").extract_first(default="").strip()
                vendor['last_active']       = self.parse_datetime(vendor['last_active'])
                vendor['public_pgp_key']    = self.get_text(response.xpath(".//section[@id='content1']//div[@class='bubble']//div[@class='pgp_box']"))
                if vendor['public_pgp_key'].endswith("BLOCK----"):
                    self.logger.warning("PGP key is missing a last letter '-' so adding it. Page %s" % response.url)
                    vendor['public_pgp_key'] = vendor['public_pgp_key'] + "-"
                vendor['public_pgp_key']    = self.normalize_pgp_key(vendor['public_pgp_key'])
                vendor['join_date']         = response.xpath(".//section[@id='content1']//label[contains(text(),'Member Since')]/following-sibling::span/text()").extract_first(default="").strip()
                vendor['join_date']         = self.parse_datetime(vendor['join_date'])
                vendor['feedback_received'] = response.xpath(".//section[@id='content1']//label[contains(text(),'Feedback Score')]/following-sibling::span/text()").extract_first(default="").strip()
                vendor['ship_from']         = response.xpath(".//section[@id='content1']//label[contains(text(),'Shipping From')]/following-sibling::span/text()").extract_first(default="").strip()
                vendor['ship_to']           = response.xpath(".//section[@id='content1']//label[contains(text(),'Shipping To')]/following-sibling::span/text()").extract_first(default="").strip()
                vendor['profile']           = self.get_text(response.xpath(".//section[@id='content1']//div[@class='bubble']/p"))
                vendor['successful_transactions'] = response.xpath(".//section[@id='content1']//label[contains(text(), 'Sales')]/following-sibling::span/text()").extract_first(default="").strip()
                # new fields
                vendor['response_time'] = response.xpath(".//section[@id='content1']//label[contains(text(), 'Average Message Response Time')]/following-sibling::span/text()").extract_first(default="").strip()
                vendor['vacation_mode'] = self.get_text(response.xpath(".//section[@id='content1']//div[@class='row nomargin']//div[@class='col-2']/span[contains(@style,'color')]"))
                vacation_mode_normalized = re.search(r"([\w\s]+)", vendor['vacation_mode'], re.M | re.I)
                if vacation_mode_normalized:
                    vendor['vacation_mode'] = vacation_mode_normalized.group(1).strip()
                yield vendor
            except Exception as error:
                self.logger.warning("Couldn't yield vendor from %s (Error: %s)" % (response.url, error))

            # Yield ratings.
            feedbacks = response.xpath(".//section[@id='content2']//div[@class='feedback']")
            if feedbacks:
                for feedback in feedbacks:
                    try:
                        rating                      = items.UserRating()
                        rating['username']          = response.xpath(".//section[@id='content1']//span[@class='feedbackScore']/../text()").extract_first(default="").strip()
                        if rating['username'] is None or len(rating['username']) < 2:
                            inspect_response(response, self)
                        ads_id = feedback.xpath("div[@class='feedback_header']/a/@href").extract_first()
                        if ads_id is not None:
                            rating['ads_id']            = self.get_url_param(ads_id,'lid')
                        rating['submitted_by']      = feedback.xpath("div[@class='feedback_header']//span[@class='feedbackScore']/../text()").extract_first(default="").strip()
                        rating['item_name']         = feedback.xpath("div[@class='feedback_header']/a/text()").extract_first(default="").strip()
                        submitted_on_string         = feedback.xpath("div[@class='feedback_header']/span/text()").extract_first(default="").strip()
                        if 'Private Listing' in submitted_on_string:
                            submitted_on_string = feedback.xpath("div[@class='feedback_header']/span/span/span/text()").extract_first()
                        rating['submitted_on_string'] = submitted_on_string
                        rating['submitted_on']        = self.parse_datetime(submitted_on_string)
                        rating['submitted_by_number_transactions'] = self.get_text(feedback.xpath("div[@class='feedback_header']//span[@class='feedbackScore']/sub"))
                        rating['submitter_rating']  = self.get_text(feedback.xpath("div[@class='feedback_header']//span[@class='feedbackScore']/sup"))
                        rating['comment']           = self.get_text(feedback.xpath("p"))
                        rating['price_usd']         = feedback.xpath("div[@class='feedback_subheader']/div/span/text()[contains(., 'USD')]").extract_first()
                        rating['price_usd']         = rating['price_usd'].replace("~", "").replace("USD", "").replace(" ", "")
                        rating_star                 = feedback.xpath("div[@class='feedback_subheader']//div[contains(@style,'img/star.png')]/@style").extract_first(default="")
                        rating_star                 = re.search(r"width:(\d+)px;height", rating_star, re.M | re.S)
                        if rating_star:
                            rating_star             = float(rating_star.group(1))
                            rating['rating']        = rating_star / 120 * 5
                        warning = feedback.xpath("div[@class='feedback_subheader']/div/span")
                        if warning and len(warning) > 1:
                            rating['warnings'] = self.get_text(warning[0])
                        yield rating
                    except Exception as error:
                        self.logger.warning("Couldn't yield feedbacks from %s (Error: %s)" % (response.url, error))
        else:
            self.logger.warning("Encountered a buyer profile. Skipping page %s. This should NOT happen." % response.url)
