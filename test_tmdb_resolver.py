import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import tmdb_resolver as tmdb

class Tests(unittest.TestCase):
 def test_normalization(self):
  self.assertEqual(tmdb._norm('Spider-Man: Homecoming'),'spidermanhomecoming')

 def test_exact_title_year_is_required(self):
  search={'results':[
   {'id':1,'title':'Heat','original_title':'Heat','release_date':'1995-12-15'},
   {'id':2,'title':'Heat','original_title':'Heat','release_date':'1986-03-14'},
  ]}
  with patch.object(tmdb,'_get',return_value=search), patch.object(tmdb,'_details',return_value={'tmdb_id':1}) as details:
   result=tmdb._search_exact('Heat',1995)
  self.assertEqual(result,{'tmdb_id':1})
  details.assert_called_once_with(1)

 def test_ambiguous_exact_match_is_refused(self):
  search={'results':[
   {'id':1,'title':'Crash','original_title':'Crash','release_date':'1996-01-01'},
   {'id':2,'title':'Crash','original_title':'Crash','release_date':'1996-02-01'},
  ]}
  with patch.object(tmdb,'_get',return_value=search), patch.object(tmdb,'_details') as details:
   result=tmdb._search_exact('Crash',1996)
  self.assertIsNone(result)
  details.assert_not_called()

 def test_compact_builds_links_and_poster(self):
  details={'id':99,'title':'Example','original_title':'Example','release_date':'2020-04-01','poster_path':'/abc.jpg','vote_average':7.5,'vote_count':100,'runtime':102,'genres':[{'name':'Drama'}],'external_ids':{'imdb_id':'tt123'}}
  row=tmdb._compact(details)
  self.assertEqual(row['tmdb_id'],99)
  self.assertEqual(row['imdb_id'],'tt123')
  self.assertEqual(row['year'],'2020')
  self.assertTrue(row['poster_url'].endswith('/abc.jpg'))
  self.assertEqual(row['genres'],['Drama'])

 def test_cache_is_used_before_network(self):
  with tempfile.TemporaryDirectory() as d:
   cache_path=Path(d)/'cache.json'
   cache_path.write_text('{"title:example:2020":{"tmdb_id":99,"title":"Example"}}')
   with patch.object(tmdb,'CACHE_PATH',cache_path), patch.object(tmdb,'TOKEN','token'), patch.object(tmdb,'_search_exact') as search:
    result=tmdb.resolve_movie('Example',2020)
   self.assertEqual(result['tmdb_id'],99)
   search.assert_not_called()

if __name__=='__main__':unittest.main()
