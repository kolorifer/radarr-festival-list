import unittest
from unittest.mock import patch
import movie_intel_service as svc

REAL_REJECTION = {
 "event":"action.rejected",
 "data":{
  "release":{"type":"movie","name":"Slaughter In San Francisco 1974 US CUT DUBBED 720p BluRay x264-RUSTED","title":"Slaughter In San Francisco","year":1974,"download_url":"SECRET"},
  "result":{"status":"PUSH_REJECTED","rejections":["Unknown Movie. Unable to match to existing movie in Library using release title."]}
 }
}

class Tests(unittest.TestCase):
 def test_real_unknown_movie_is_safe_and_useful(self):
  with patch.object(svc,'INDEX',{}):
   text=svc.format_message(REAL_REJECTION)
  self.assertIn('Unknown Movie',text)
  self.assertIn('Slaughter In San Francisco',text)
  self.assertIn('Unable to match',text)
  self.assertNotIn('SECRET',text)
  self.assertNotIn('download_url',text)

 def test_qualified_movie_flag(self):
  movie={'imdb_id':'tt1','title':'Example','year':2020,'imdb':{'rating':8.1,'votes':123456},'letterboxd':{'rating':4.2,'ratings':50000},'tspdt_rank':321,'institutional_signals':['Oscar Best Picture nominee'],'qualified':True,'routes':['convergence']}
  payload={'event':'action.rejected','data':{'release':{'type':'movie','title':'Example','year':2020},'result':{'rejections':['Unknown Movie']}}}
  meta={'tmdb_id':99,'imdb_id':'tt1','title':'Example','year':'2020','genres':['Drama'],'runtime':102}
  text=svc.format_message(payload,movie=movie,meta=meta)
  self.assertIn('IMDb 8.1',text)
  self.assertIn('Letterboxd 4.2',text)
  self.assertIn('TSPDT #321',text)
  self.assertNotIn('POTENTIAL FALSE NEGATIVE',text)
  self.assertIn('Our model: QUALIFIES',text)
  self.assertIn('convergence',text)
  self.assertIn('href="https://www.imdb.com/title/tt1/"',text)
  self.assertIn('href="https://www.themoviedb.org/movie/99"',text)
  self.assertIn('1h 42m',text)

 def test_topic_id_is_added_as_message_thread_id(self):
  with patch.object(svc,'TELEGRAM_CHAT_ID','-100123'), patch.object(svc,'TELEGRAM_TOPIC_ID','42'):
   body=svc._telegram_payload('hello')
  self.assertEqual(body['message_thread_id'],42)
  self.assertEqual(body['chat_id'],'-100123')

 def test_topic_is_optional(self):
  with patch.object(svc,'TELEGRAM_CHAT_ID','-100123'), patch.object(svc,'TELEGRAM_TOPIC_ID',''):
   body=svc._telegram_payload('hello')
  self.assertNotIn('message_thread_id',body)

 def test_photo_payload_keeps_topic_and_caption(self):
  with patch.object(svc,'TELEGRAM_CHAT_ID','-100123'), patch.object(svc,'TELEGRAM_TOPIC_ID','42'):
   body=svc._telegram_photo_payload('https://image.invalid/poster.jpg','<b>Example</b>')
  self.assertEqual(body['photo'],'https://image.invalid/poster.jpg')
  self.assertEqual(body['caption'],'<b>Example</b>')
  self.assertEqual(body['message_thread_id'],42)
  self.assertEqual(body['parse_mode'],'HTML')

 def test_plain_passthrough_has_no_html_parse_mode(self):
  with patch.object(svc,'TELEGRAM_CHAT_ID','-100123'), patch.object(svc,'TELEGRAM_TOPIC_ID',''):
   body=svc._telegram_payload('<test>', parse_mode=None)
  self.assertEqual(body['text'],'<test>')
  self.assertNotIn('parse_mode',body)

 def test_passthrough_prefers_original_message(self):
  payload={'event':'test','message':'autobrr webhook test <unchanged>'}
  self.assertEqual(svc.passthrough_message(payload),'autobrr webhook test <unchanged>')

 def test_passthrough_sanitizes_structured_secrets(self):
  payload={'event':'test','data':{'download_url':'https://tracker.invalid/SECRET','token':'abc','name':'safe'}}
  text=svc.passthrough_message(payload)
  self.assertIn('[redacted]',text)
  self.assertIn('safe',text)
  self.assertNotIn('SECRET',text)
  self.assertNotIn('abc',text)

 def test_routine_release_rejection_has_no_cache_warning(self):
  payload={'event':'action.rejected','data':{'release':{'type':'movie','title':'One Night Only','year':2026,'name':'One Night Only 2026 2160p'},'result':{'rejections':['Bluray-2160p is not wanted in profile','Existing file meets cutoff: Remux-2160p']}}}
  text=svc.format_message(payload,movie=None,meta=None)
  self.assertIn('Release Rejected',text)
  self.assertNotIn('local intelligence',text)
  self.assertNotIn('Our model',text)

 def test_build_notification_uses_tmdb_poster(self):
  payload={'event':'action.rejected','data':{'release':{'type':'movie','title':'Example','year':2020},'result':{'rejections':['Unknown Movie']}}}
  meta={'tmdb_id':99,'imdb_id':'tt9','title':'Example','year':'2020','poster_url':'https://image.invalid/p.jpg','genres':[],'runtime':90,'tmdb_rating':7.0,'tmdb_votes':100}
  with patch.object(svc,'INDEX',{}), patch.object(svc,'resolve_movie',return_value=meta) as resolver:
   text,poster=svc.build_movie_notification(payload)
  resolver.assert_called_once_with('Example',2020,imdb_id=None)
  self.assertEqual(poster,'https://image.invalid/p.jpg')
  self.assertIn('TMDb 7.0',text)

if __name__=='__main__':unittest.main()
