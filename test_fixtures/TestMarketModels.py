import sys
from os import path
import random
import string
import unittest
from datetime import datetime, timedelta
from scrapyprj.database import db
from scrapyprj.database.settings import markets as dbsetting
from scrapyprj.database.markets.orm.models import *
from IPython import embed

class TestMarketModels(unittest.TestCase):

	def randstring(self, length):
		return ''.join(random.choice(string.ascii_uppercase  + string.digits) for _ in range(length))
	
	def create_market(self):
		return Market(name=self.randstring(50), spider=self.randstring(50))

	def create_process(self):
		return Process(start=self.random_datetime(), end=self.random_datetime(), pid=random.randint(0,9999999), cmdline = self.randstring(100))

	def create_scrape(self, market, process):
		return Scrape(process=process, market=market, start=self.random_datetime(), end=self.random_datetime(), reason=self.randstring(100), login=self.randstring(100), proxy=self.randstring(100))

	def create_market_process_scrape(self):
		market = self.create_market()
		process = self.create_process()
		scrape = self.create_scrape(market, process)

		return (market, process, scrape)

	def round_microseconds(self, dt):
		if dt.microsecond >= 500000:
			dt += timedelta(seconds = 1);

		return dt.replace(microsecond=0)

	def random_datetime(self):
		year = random.randint(1970, 2017)
		month = random.randint(1, 12)
		day = random.randint(1, 28)
		hours = random.randint(0,23)
		minutes = random.randint(0,59)
		seconds = random.randint(0,59)
		return datetime(year, month, day, hours, minutes, seconds)


######################################
	def setUp(self):
		db.init(dbsetting)


	def test_market(self):
		market = self.create_market()
		market.save(force_insert=True)
		try:
			market2 = Market.get(id=market.id)
			self.assertEqual(market2.id, market.id)
			self.assertEqual(market2.spider, market.spider)
			self.assertEqual(market2.name, market.name)
		except:
			try:
				market.delete_instance() 
			except: pass
			raise
		
		market.delete_instance()


	def test_process(self):
		process = self.create_process()
		process.save()

		try:
			process2 = Process.get(id=process.id)
			self.assertEqual(process.id, process2.id)
			self.assertEqual(self.round_microseconds(process.start), process2.start)
			self.assertEqual(self.round_microseconds(process.end), process2.end)
			self.assertEqual(process.pid, process2.pid)
			self.assertEqual(process.cmdline, process2.cmdline)
		except:
			try:
				process.delete_instance()
			except: pass
			raise
		
		process.delete_instance()


	def test_scrape(self):
		market, process, scrape = self.create_market_process_scrape()
		market.save(force_insert=True)
		process.save(force_insert=True)
		scrape.save(force_insert=True)

		try:
			scrape2 = Scrape.get(id=scrape.id)
			self.assertEqual(scrape.id, scrape2.id)
			self.assertEqual(scrape.process.id, scrape2.process.id)
			self.assertEqual(scrape.market.id, scrape2.market.id)
			self.assertEqual(self.round_microseconds(scrape.start), scrape2.start)
			self.assertEqual(self.round_microseconds(scrape.end), scrape2.end)
			self.assertEqual(scrape.reason, scrape2.reason)
			self.assertEqual(scrape.login, scrape2.login)
			self.assertEqual(scrape.proxy, scrape2.proxy)
		except:
			try:
				scrape.delete_instance()
				process.delete_instance()
				market.delete_instance()
			except: pass
			raise
		
		scrape.delete_instance()
		process.delete_instance()
		market.delete_instance()


	def test_scrapestat(self):
		market, process, scrape = self.create_market_process_scrape()
		market.save(force_insert=True)
		process.save(force_insert=True)
		scrape.save(force_insert=True)

		scrapestat = ScrapeStat(scrape = scrape,logtime = self.random_datetime(),request_sent = 1,request_bytes = 2,response_received = 3,response_bytes =  4 ,item_scraped = 5,ads = 6	,ads_propval =	7,ads_feedback =8	,ads_feedback_propval = 9,user = 10,user_propval =11,seller_feedback =12,seller_feedback_propval =13)
		scrapestat.save()

		try:
			scrapestat2 = ScrapeStat.get(id=scrapestat.id)
			self.assertEqual(scrapestat.id,scrapestat2.id )
			self.assertEqual(scrapestat.scrape.id,scrapestat2.scrape.id )
			self.assertEqual(self.round_microseconds(scrapestat.logtime),scrapestat2.logtime )
			self.assertEqual(scrapestat.request_sent,scrapestat2.request_sent )
			self.assertEqual(scrapestat.request_bytes,scrapestat2.request_bytes )
			self.assertEqual(scrapestat.response_received,scrapestat2.response_received )
			self.assertEqual(scrapestat.response_bytes,scrapestat2.response_bytes )
			self.assertEqual(scrapestat.item_scraped,scrapestat2.item_scraped )
			self.assertEqual(scrapestat.ads,scrapestat2.ads )
			self.assertEqual(scrapestat.ads_propval,scrapestat2.ads_propval )
			self.assertEqual(scrapestat.ads_feedback,scrapestat2.ads_feedback )
			self.assertEqual(scrapestat.ads_feedback_propval,scrapestat2.ads_feedback_propval )
			self.assertEqual(scrapestat.user,scrapestat2.user )
			self.assertEqual(scrapestat.user_propval,scrapestat2.user_propval )
			self.assertEqual(scrapestat.seller_feedback,scrapestat2.seller_feedback )
			self.assertEqual(scrapestat.seller_feedback_propval,scrapestat2.seller_feedback_propval )
		except:
			try:
				scrapestat.delete_instance()
				scrape.delete_instance()
				process.delete_instance()
				market.delete_instance()
			except: pass
			raise
		scrapestat.delete_instance()
		scrape.delete_instance()
		process.delete_instance()
		market.delete_instance()


	def test_captcha_question(self):
		market = self.create_market()
		market.save(force_insert=True)
		cq = CaptchaQuestion(market = market, hash='1234', question ='How are you', answer='fine')
		cq.save(force_insert=True)

		try:
			cq2 = CaptchaQuestion.get(id=cq.id)

			self.assertEqual(cq.id, cq2.id)
			self.assertEqual(cq.market.id, cq2.market.id)
			self.assertEqual(cq.hash, cq2.hash)
			self.assertEqual(cq.question, cq2.question)
			self.assertEqual(cq.answer, cq2.answer)
		except:
			try:
				cq.delete_instance()
				market.delete_instance()
			except: pass
			raise
		
		cq.delete_instance()
		market.delete_instance()


##### User ############

	def test_user(self):
		market, process, scrape = self.create_market_process_scrape()
		market.save(force_insert=True)
		process.save(force_insert=True)
		scrape.save(force_insert=True)

		user = User(market = market, scrape=scrape, username=self.randstring(100), relativeurl=self.randstring(100), fullurl=self.randstring(100))
		user.save(force_insert=True)
		try:
			user2 = User.get(id=user.id)

			self.assertEqual(user.id, user2.id)
			self.assertEqual(user.market.id, user2.market.id)
			self.assertEqual(user.scrape.id, user2.scrape.id)
			self.assertEqual(user.relativeurl, user2.relativeurl)
			self.assertEqual(user.fullurl, user2.fullurl)
		except:
			try:
				user.delete_instance()
				scrape.delete_instance()
				process.delete_instance()
				market.delete_instance()
			except: pass
			raise
		
		user.delete_instance()
		scrape.delete_instance()
		process.delete_instance()
		market.delete_instance()

	def test_user_propkey(self):
		propkey = UserPropertyKey(name = self.randstring(50))
		propkey.save(force_insert=True)
		try:
			propkey2 = UserPropertyKey.get(id=propkey.id)

			self.assertEqual(propkey.id, propkey2.id)
			self.assertEqual(propkey.name, propkey2.name)
		except:
			try:
				propkey.delete_instance()

			except: pass
			raise
		
		propkey.delete_instance()


	def test_user_propval(self):
		market, process, scrape = self.create_market_process_scrape()
		market.save(force_insert=True)
		process.save(force_insert=True)
		scrape.save(force_insert=True)

		user = User(market = market, scrape=scrape, username=self.randstring(100), relativeurl=self.randstring(100), fullurl=self.randstring(100))
		user.save(force_insert=True)
		propkey = UserPropertyKey(name = self.randstring(50))
		propkey.save(force_insert=True)
		propval = UserProperty(key = propkey, owner = user, data = self.randstring(10000), scrape=scrape)
		propval.save(force_insert=True)
		try:
			propval2 = UserProperty.get(owner=user.id, key=propkey.id)
			self.assertEqual(propval.key.id, propval2.key.id)
			self.assertEqual(propval.owner.id, propval2.owner.id)
			self.assertEqual(propval.data, propval2.data)
			self.assertEqual(propval.scrape.id, propval2.scrape.id)
		except:
			try:
				propval.delete_instance()
				propkey.delete_instance()
				user.delete_instance()
				scrape.delete_instance()
				process.delete_instance()
				market.delete_instance()
			except: pass
			raise
		
		propval.delete_instance()
		propkey.delete_instance()
		user.delete_instance()
		scrape.delete_instance()
		process.delete_instance()
		market.delete_instance()
########################



########## Ads #############

	def test_ads(self):
		market, process, scrape = self.create_market_process_scrape()
		market.save(force_insert=True)
		process.save(force_insert=True)
		scrape.save(force_insert=True)
		user = User(market = market, scrape=scrape, username=self.randstring(100), relativeurl=self.randstring(100), fullurl=self.randstring(100))
		user.save(force_insert=True)
		ads = Ads(market = market, scrape=scrape, external_id=self.randstring(100), title=self.randstring(100), seller=user, relativeurl=self.randstring(100), fullurl=self.randstring(100), last_update=self.random_datetime())
		ads.save(force_insert=True)
		try:
			ads2 = Ads.get(id=ads.id)

			self.assertEqual(ads.id, ads2.id)
			self.assertEqual(ads.market.id, ads2.market.id)
			self.assertEqual(ads.scrape.id, ads2.scrape.id)
			self.assertEqual(ads.relativeurl, ads2.relativeurl)
			self.assertEqual(ads.fullurl, ads2.fullurl)
			self.assertEqual(ads.external_id, ads2.external_id)
			self.assertEqual(ads.title, ads2.title)
			self.assertEqual(self.round_microseconds(ads.last_update), ads2.last_update)
		except:
			try:
				ads.delete_instance()
				user.delete_instance()
				scrape.delete_instance()
				process.delete_instance()
				market.delete_instance()
			except: pass
			raise
		
		ads.delete_instance()
		user.delete_instance()
		scrape.delete_instance()
		process.delete_instance()
		market.delete_instance()

	def test_ads_propkey(self):
		propkey = AdsPropertyKey(name = self.randstring(50))
		propkey.save(force_insert=True)
		try:
			propkey2 = AdsPropertyKey.get(id=propkey.id)

			self.assertEqual(propkey.id, propkey2.id)
			self.assertEqual(propkey.name, propkey2.name)
		except:
			try:
				propkey.delete_instance()

			except: pass
			raise
		
		propkey.delete_instance()


	def test_ads_propval(self):
		market, process, scrape = self.create_market_process_scrape()
		market.save(force_insert=True)
		process.save(force_insert=True)
		scrape.save(force_insert=True)

		user = User(market = market, scrape=scrape, username=self.randstring(100), relativeurl=self.randstring(100), fullurl=self.randstring(100))
		user.save(force_insert=True)
		ads = Ads(market = market, scrape=scrape, external_id=self.randstring(100), title=self.randstring(100), seller=user, relativeurl=self.randstring(100), fullurl=self.randstring(100), last_update=self.random_datetime())
		ads.save(force_insert=True)
		propkey = AdsPropertyKey(name = self.randstring(50))
		propkey.save(force_insert=True)
		propval = AdsProperty(key = propkey, owner = ads, data = self.randstring(10000), scrape=scrape)
		propval.save(force_insert=True)
		try:
			propval2 = AdsProperty.get(owner=ads.id, key=propkey.id)
			self.assertEqual(propval.key.id, propval2.key.id)
			self.assertEqual(propval.owner.id, propval2.owner.id)
			self.assertEqual(propval.data, propval2.data)
			self.assertEqual(propval.scrape.id, propval2.scrape.id)
		except:
			try:
				propval.delete_instance()
				propkey.delete_instance()
				ads.delete_instance()
				user.delete_instance()
				scrape.delete_instance()
				process.delete_instance()
				market.delete_instance()
			except: pass
			raise
		
		propval.delete_instance()
		propkey.delete_instance()
		ads.delete_instance()
		user.delete_instance()
		scrape.delete_instance()
		process.delete_instance()
		market.delete_instance()
#####################


########## SellerFeedback #############

	def test_seller_feedback(self):
		market, process, scrape = self.create_market_process_scrape()
		market.save(force_insert=True)
		process.save(force_insert=True)
		scrape.save(force_insert=True)
		user = User(market = market, scrape=scrape, username=self.randstring(100), relativeurl=self.randstring(100), fullurl=self.randstring(100))
		user.save(force_insert=True)
		sf = SellerFeedback(market = market, scrape=scrape, external_id=self.randstring(100), seller=user)
		sf.save(force_insert=True)
		try:
			sf2 = SellerFeedback.get(id=sf.id)

			self.assertEqual(sf.id, sf2.id)
			self.assertEqual(sf.market.id, sf2.market.id)
			self.assertEqual(sf.scrape.id, sf2.scrape.id)
			self.assertEqual(sf.seller.id, sf2.seller.id)
			self.assertEqual(sf.external_id, sf2.external_id)
		except:
			try:
				sf.delete_instance()
				user.delete_instance()
				scrape.delete_instance()
				process.delete_instance()
				market.delete_instance()
			except: pass
			raise
		
		sf.delete_instance()
		user.delete_instance()
		scrape.delete_instance()
		process.delete_instance()
		market.delete_instance()

	def test_seller_feedback_propkey(self):
		propkey = SellerFeedbackPropertyKey(name = self.randstring(50))
		propkey.save(force_insert=True)
		try:
			propkey2 = SellerFeedbackPropertyKey.get(id=propkey.id)

			self.assertEqual(propkey.id, propkey2.id)
			self.assertEqual(propkey.name, propkey2.name)
		except:
			try:
				propkey.delete_instance()

			except: pass
			raise
		
		propkey.delete_instance()


	def test_seller_feedback_propval(self):
		market, process, scrape = self.create_market_process_scrape()
		market.save(force_insert=True)
		process.save(force_insert=True)
		scrape.save(force_insert=True)

		user = User(market = market, scrape=scrape, username=self.randstring(100), relativeurl=self.randstring(100), fullurl=self.randstring(100))
		user.save(force_insert=True)
		sf = SellerFeedback(market = market, scrape=scrape, external_id=self.randstring(100), seller=user)
		sf.save(force_insert=True)
		propkey = SellerFeedbackPropertyKey(name = self.randstring(50))
		propkey.save(force_insert=True)
		propval = SellerFeedbackProperty(key = propkey, owner = sf, data = self.randstring(10000), scrape=scrape)
		propval.save(force_insert=True)
		try:
			propval2 = SellerFeedbackProperty.get(owner=sf.id, key=propkey.id)
			self.assertEqual(propval.key.id, propval2.key.id)
			self.assertEqual(propval.owner.id, propval2.owner.id)
			self.assertEqual(propval.data, propval2.data)
			self.assertEqual(propval.scrape.id, propval2.scrape.id)
		except:
			try:
				propval.delete_instance()
				propkey.delete_instance()
				sf.delete_instance()
				user.delete_instance()
				scrape.delete_instance()
				process.delete_instance()
				market.delete_instance()
			except: pass
			raise
		
		propval.delete_instance()
		propkey.delete_instance()
		sf.delete_instance()
		user.delete_instance()
		scrape.delete_instance()
		process.delete_instance()
		market.delete_instance()





########## Ads Feedback #############

	def test_ads_feedback(self):
		market, process, scrape = self.create_market_process_scrape()
		market.save(force_insert=True)
		process.save(force_insert=True)
		scrape.save(force_insert=True)
		user = User(market = market, scrape=scrape, username=self.randstring(100), relativeurl=self.randstring(100), fullurl=self.randstring(100))
		user.save(force_insert=True)		
		ads = Ads(market = market, scrape=scrape, external_id=self.randstring(100), title=self.randstring(100), seller=user, relativeurl=self.randstring(100), fullurl=self.randstring(100), last_update=self.random_datetime())
		ads.save(force_insert=True)
		af = AdsFeedback(market = market, scrape=scrape, external_id=self.randstring(100), ads=ads)
		af.save(force_insert=True)
		try:
			af2 = AdsFeedback.get(id=af.id)

			self.assertEqual(af.id, af2.id)
			self.assertEqual(af.market.id, af2.market.id)
			self.assertEqual(af.scrape.id, af2.scrape.id)
			self.assertEqual(af.ads.id, af2.ads.id)
			self.assertEqual(af.external_id, af2.external_id)
		except:
			try:
				af.delete_instance()
				ads.delete_instance()
				scrape.delete_instance()
				process.delete_instance()
				market.delete_instance()
			except: pass
			raise
		
		af.delete_instance()
		ads.delete_instance()
		scrape.delete_instance()
		process.delete_instance()
		market.delete_instance()

	def test_ads_feedback_propkey(self):
		propkey = AdsFeedbackPropertyKey(name = self.randstring(50))
		propkey.save(force_insert=True)
		try:
			propkey2 = AdsFeedbackPropertyKey.get(id=propkey.id)

			self.assertEqual(propkey.id, propkey2.id)
			self.assertEqual(propkey.name, propkey2.name)
		except:
			try:
				propkey.delete_instance()
			except: pass
			raise
		propkey.delete_instance()


	def test_ads_feedback_propval(self):
		market, process, scrape = self.create_market_process_scrape()
		market.save(force_insert=True)
		process.save(force_insert=True)
		scrape.save(force_insert=True)

		user = User(market = market, scrape=scrape, username=self.randstring(100), relativeurl=self.randstring(100), fullurl=self.randstring(100))
		user.save(force_insert=True)
		ads = Ads(market = market, scrape=scrape, external_id=self.randstring(100), title=self.randstring(100), seller=user, relativeurl=self.randstring(100), fullurl=self.randstring(100), last_update=self.random_datetime())
		ads.save(force_insert=True)
		af = AdsFeedback(market = market, scrape=scrape, external_id=self.randstring(100), ads=ads)
		af.save(force_insert=True)
		propkey = AdsFeedbackPropertyKey(name = self.randstring(50))
		propkey.save(force_insert=True)
		propval = AdsFeedbackProperty(key = propkey, owner = af, data = self.randstring(10000), scrape=scrape)
		propval.save(force_insert=True)
		try:
			propval2 = AdsFeedbackProperty.get(owner=af.id, key=propkey.id)
			self.assertEqual(propval.key.id, propval2.key.id)
			self.assertEqual(propval.owner.id, propval2.owner.id)
			self.assertEqual(propval.data, propval2.data)
			self.assertEqual(propval.scrape.id, propval2.scrape.id)
		except:
			try:
				propval.delete_instance()
				propkey.delete_instance()
				af.delete_instance()
				user.delete_instance()
				scrape.delete_instance()
				process.delete_instance()
				market.delete_instance()
			except: pass
			raise
		
		propval.delete_instance()
		propkey.delete_instance()
		af.delete_instance()
		user.delete_instance()
		scrape.delete_instance()
		process.delete_instance()
		market.delete_instance()