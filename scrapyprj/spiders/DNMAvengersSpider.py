from __future__ import absolute_import
import scrapy
from scrapy.http import FormRequest,Request
from scrapy.shell import inspect_response
from scrapyprj.spiders.ForumSpiderV3 import ForumSpiderV3
from scrapyprj.database.orm import *
import scrapyprj.database.forums.orm.models as models
import scrapyprj.items.forum_items as items
from datetime import datetime, timedelta
from urlparse import urlparse, parse_qsl
import logging
import time
import hashlib 
import traceback
import re
import pytz
import dateutil
from IPython import embed
from random import randint


class DNMAvengersSpider(ForumSpiderV3):
    name = "dnmavengers_forum"  
    custom_settings = {
        'MAX_LOGIN_RETRY' : 10,
        'RANDOMIZE_DOWNLOAD_DELAY' : True,
        'HTTPERROR_ALLOW_ALL' : True,
        'RETRY_ENABLED' : True,
        'RETRY_TIMES' : 5
    }

    headers = {
        'User-Agent':' Mozilla/5.0 (Windows NT 6.1; rv:52.0) Gecko/20100101 Firefox/52.0',
    }

    def __init__(self, *args, **kwargs):
        super(DNMAvengersSpider, self).__init__(*args, **kwargs)

        self.set_max_concurrent_request(1)      # Scrapy config
        self.set_download_delay(10)             # Scrapy config
        self.set_max_queue_transfer_chunk(1)    # Custom Queue system
        self.statsinterval = 60                 # Custom Queue system
        self.logintrial = 0                     # Max login attempts.
        self.alt_hostnames = []                 # Not in use.
        self.report_status = True               # Report 200's.
        self.loggedin = False                   # Login flag. 

    def start_requests(self):
        yield self.make_request(url = 'index', dont_filter=True)

    def make_request(self, reqtype='regular', **kwargs):
        if 'url' in kwargs:
            kwargs['url'] = self.make_url(kwargs['url'])
        # Handle the requests.
        # If you need to bypass DDoS protection, put it in here.
        if reqtype is 'dologin':
            req = self.craft_login_request_from_form(kwargs['response']) 
            req.dont_filter = True
        elif reqtype is 'loginpage':
            req = Request(self.make_url('loginpage'), headers=self.headers, dont_filter=True)
        elif reqtype is 'regular':
            req = Request(kwargs['url'], headers=self.headers)
            req.meta['shared'] = True # Ensures that requests are shared among spiders.

        # Some meta-keys that are shipped with the request.
        if 'relativeurl' in kwargs:
            req.meta['relativeurl'] = kwargs['relativeurl']
        if 'dont_filter' in kwargs:
            req.dont_filter = kwargs['dont_filter']
        if 'req_once_logged' in kwargs:
            req.meta['req_once_logged'] = kwargs['req_once_logged']  
        req.meta['proxy'] = self.proxy  
        req.meta['slot'] = self.proxy
        req.meta['reqtype'] = reqtype   # We tell the type so that we can redo it if login is required
        return req

    def parse_response(self, response):
        parser = None
        # Handle login status.
        if self.islogged(response) is False:
            self.loggedin = False
            req_once_logged = response.meta['req_once_logged'] if 'req_once_logged' in response.meta else response.request
            if self.is_login_page(response) is False:
                # req_once_logged stores the request we will go to after logging in.
                yield self.make_request(reqtype='loginpage',response=response, req_once_logged=req_once_logged) 
            else:
                # Try to yield informative error messages if we can't logon.
                if self.is_login_page(response) is True and self.login_failed(response) is True:
                    self.logger.info('Failed last login as %s. Trying again. Error: %s' % (self.login['username'], self.get_text(response.xpath('.//div/ul[@class="error-list"]'))))
                # Allow the spider to fail if it can't log on.
                if self.logintrial > self.settings['MAX_LOGIN_RETRY']:
                    self.wait_for_input("Too many login failed", req_once_logged)
                    self.logintrial = 0
                    return
                self.logger.info("Trying to login as %s." % self.login['username'])
                self.logintrial += 1
                yield self.make_request(reqtype='dologin', response=response, req_once_logged=req_once_logged)
        # Handle parsing.
        else:
            self.loggedin = True
            # We restore the missed request when protection kicked in
            if response.meta['reqtype'] == 'dologin':
                self.logger.info("Succesfully logged in as %s! Returning to stored request %s" % (self.login['username'], response.meta['req_once_logged']))
                if response.meta['req_once_logged'] is None:
                    self.logger.warning("We are trying to yield a None. This should not happen.")
                yield response.meta['req_once_logged']    
            else:
                if self.is_threadlisting(response) is True:
                    parser = self.parse_threadlisting
                elif self.is_message(response) is True:
                    parser = self.parse_message
                elif self.is_user(response) is True:
                    parser = self.parse_user
                # Yield the appropriate parsing function.
                if parser is not None:
                    for x in parser(response):
                        yield x
                else:
                    self.logger.info("Unknown page type at %s" % response.url)

    ########## PARSING FLAGS ##############
    def is_message(self, response):
        if "index.php?topic=" in response.url:
            return True

    def is_user(self, response):
        if 'index.php?action=profile;u=' in response.url:
            return True

    def is_threadlisting(self, response):
        if "index.php?board=" in response.url:
            return True
            
    ########## PARSING FUNCTIONS ##########
    def parse_user(self, response):
        #self.logger.info("Yielding profile from %s" % response.url)

        user = items.User()
        user['relativeurl'] = response.url.replace("http://avengersdutyk3xf.onion", "").replace(";area=summary", "")
        user['username'] = self.get_text(response.css("#basicinfo .username h4::text").extract_first())
        user['fullurl'] = response.url.replace(";area=summary", "")
        user['membergroup'] = self.get_text(response.css("#basicinfo .username h4 span.position"))

        dts = response.css("#detailedinfo .content dl dt")
        for dt in dts:
            key = self.get_text(dt).lower().rstrip(':')
            ddtext = self.get_text(dt.xpath('following-sibling::dd[1]'))

            if key == 'posts':
                m = re.search('(\d+)\s*\((.+) per day\)', ddtext)
                if m:
                    if "N/A" not in m.group(1):
                        user['post_count'] = m.group(1)
                    if "N/A" not in m.group(2):                        
                        user['post_per_day'] = m.group(2)
                else:
                    if "N/A" not in ddtext:
                        user['post_count'] = ddtext
            elif key == 'karma':
                if "N/A" not in ddtext:
                    user['karma'] = ddtext
            elif key == 'age':
                if "N/A" not in ddtext:
                    user['age'] = ddtext
            elif key == 'position 1':
                if "N/A" not in ddtext:
                    user['group'] = ddtext
            elif key == 'gender':
                if "N/A" not in ddtext:
                    user['gender'] = ddtext
            elif key == 'personal text':
                if "N/A" not in ddtext:
                    user['personal_text'] = ddtext
            elif key == 'date registered':
                if "N/A" not in ddtext:
                    user['joined_on'] = self.parse_timestr(ddtext)
            elif key == 'last active':
                if "N/A" not in ddtext:
                    user['last_active'] = self.parse_timestr(ddtext)                
            elif key == 'location':
                if "N/A" not in ddtext:
                    user['location'] = ddtext
            elif key == 'custom title':
                if "N/A" not in ddtext:
                    user['custom_title'] = ddtext
            elif key == 'pgp':
                if "just ask me" not in ddtext:
                    user['pgp_key'] = self.normlaize_pgp_key(ddtext)
            elif key == 'email':
                if "N/A" not in ddtext:
                    user['email'] = ddtext
            elif key in ['local time']:
                pass
            else:
                self.logger.warning('New information found on use profile page : %s. (%s)' % (key, response.url))

        yield user

    def parse_message(self, response):
        #self.logger.info("Yielding messages from %s" % response.url)
        m = re.search("\?topic=(\d+)", response.url)
        if m:      
            threadid = m.group(1).strip()  

        for postwrapper in response.css(".post_wrapper"):
            messageitem = items.Message()
            postmeta = self.get_text(postwrapper.css(".flow_hidden .keyinfo div"))
            postmeta_ascii = re.sub(r'[^\x00-\x7f]',r'', postmeta).strip()
            m = re.search('on:\s*(.+)', postmeta_ascii)
            if m:
                if "N/A" not in m.group(1):
                    messageitem['posted_on'] = self.parse_timestr(m.group(1))                
            postcontent = postwrapper.css(".postarea .post").xpath("./div[contains(@id, 'msg_')]")

            m = re.search('msg_(\d+)', postcontent.xpath('@id').extract_first())
            if m:
                messageitem['postid'] = m.group(1)

            messageitem['threadid']         = threadid
            messageitem['author_username']  = self.get_text(postwrapper.css(".poster h4"))  
            messageitem['contenthtml']      = postcontent.extract_first()
            messageitem['contenttext']      = self.get_text(postcontent)

            yield messageitem

    def parse_threadlisting(self, response):
        #self.logger.info("Yielding threads from %s" % response.url)
        for threadline in response.css('#messageindex table tbody tr'):

            try:
                threaditem = items.Thread()

                threadcell = threadline.css(".subject")
                authorlink = threadcell.xpath(".//p[contains(., 'Started by')]").css('a')
                threadlink = threadcell.xpath('.//span[contains(@id, "msg_")]/a')

                threaditem['author_username'] = self.get_text_first(authorlink)
                threadurl = threadlink.xpath("@href").extract_first()
                
                m = re.search("\?topic=(\d+)", threadurl)
                if m:
                    threaditem['threadid'] = m.group(1).strip()
                threaditem['title'] = self.get_text(threadlink)
                threaditem['relativeurl'] = threadurl
                threaditem['fullurl'] = self.make_url(threadurl)

                #Last update
                lastpost_str = threadline.xpath('td[contains(@class, "lastpost")]/a/following-sibling::text()').extract_first()
                if lastpost_str:
                    if "N/A" not in lastpost_str:
                        threaditem['last_update'] = self.parse_timestr(lastpost_str.strip())

                #Stats cell
                statcellcontent = threadline.xpath('td[contains(@class, "stats")]//text()').extract()
                m1 = re.search("(\d+) Replies", statcellcontent[0])
                if m1 :
                    threaditem['replies'] = m1.group(1)

                m2 = re.search("[^\d]+(\d+) Views", statcellcontent[1])
                if m2 :
                    threaditem['views'] = m2.group(1)

                yield threaditem

            except Exception as e:
                self.logger.error("Cannot parse thread item: %s for reason:" % (response.url, e))
                raise

    ############ LOGIN HANDLING ################
    def login_failed(self, response):
        if len(response.xpath('.//div/ul[@class="error-list"]')) > 0:
            return True

    def islogged(self, response):
        if 'Logout' in response.text:
            self.loggedin = True 
            return True
        return False

    def is_login_page(self, response):
        if len(response.css("#frmLogin")) > 0:
            return True
        return False

    def craft_login_request_from_form(self, response):
        sessionid = response.css('#frmLogin::attr(onsubmit)').re("'(.+)'")
        if len(sessionid) > 0:
            sessionid = sessionid[0]
            self.logger.debug("Session ID : %s" % sessionid)
        else:
            sessionid = ''
            self.logger.warning("Cannot determine session id from form")

        data = {
            'user' : self.login['username'],
            'passwrd' : self.login['password'],
            'cookielength' : '1200',
            'cookieneverexp' : 'On',
            'hash_passwrd' : self.make_hash(self.login['username'], self.login['password'], sessionid)
        }

        req = FormRequest.from_response(response, formid='frmLogin', headers=self.headers, formdata=data)

        return req

    #So there's a simili-protection on the login page where we need to submit a hash of the password salted with the session id.
    def make_hash(self, u, p, sessid):
        return hashlib.sha1(hashlib.sha1(u.encode('utf8')+p.encode('utf8')).hexdigest()+sessid).hexdigest()

    ########### MISCELLANEOUS ###################
    def parse_timestr(self, timestr):
        last_post_time = None
      
        try:
            timestr = timestr.lower()
            timestr = timestr.replace('today', str(self.localnow().date()))
            timestr = timestr.replace('yesterday', str(self.localnow().date() - timedelta(days=1)))
            last_post_time = self.to_utc(dateutil.parser.parse(timestr))
        except:
            if timestr:
                self.logger.warning("Could not determine time from this string : '%s'. Ignoring" % timestr)

        return last_post_time

    def normlaize_pgp_key(self, key):
        begin = '-----BEGIN PGP (PUBLIC|PRIVATE) KEY BLOCK-----'
        end = '-----END PGP (PUBLIC|PRIVATE) KEY BLOCK-----'
        m = re.search('(%s)(.+)(%s)' % (begin, end), key,re.S)
        if m:
            newlines = []
            for line in m.group(3).splitlines():
                if re.search('version', line, re.IGNORECASE):
                    continue
                elif re.search('comment', line, re.IGNORECASE):
                    continue
                newlines.append(line)
            content = ''.join(newlines)
            return '%s\n\n%s\n%s' % (m.group(1), content, m.group(4))        
        self.logger.warning('Failed to clean PGP key. \n %s' % key)
        return None