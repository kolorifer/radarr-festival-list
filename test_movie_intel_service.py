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
  self.assertIn('UNKNOWN MOVIE',text)
  self.assertIn('Slaughter In San Francisco',text)
  self.assertIn('Unable to match',text)
  self.assertNotIn('SECRET',text)
  self.assertNotIn('download_url',text)

 def test_qualified_movie_flag(self):
  movie={'imdb_id':'tt1','title':'Example','year':2020,'imdb':{'rating':8.1,'votes':123456},'letterboxd':{'rating':4.2,'ratings':50000},'tspdt_rank':321,'institutional_signals':['Oscar Best Picture nominee'],'qualified':True,'routes':['convergence']}
  payload={'event':'action.rejected','data':{'release':{'type':'movie','title':'Example','year':2020},'result':{'rejections':['Unknown Movie']}}}
  with patch.object(svc,'INDEX',{'tt1':movie}):
   text=svc.format_message(payload)
  self.assertIn('IMDb 8.1',text)
  self.assertIn('Letterboxd 4.2',text)
  self.assertIn('TSPDT #321',text)
  self.assertIn('POTENTIAL FALSE NEGATIVE',text)
  self.assertIn('convergence',text)

if __name__=='__main__':unittest.main()
