import unittest
from movie_intel import _norm,find_local,rejection_class
class Tests(unittest.TestCase):
 def test_norm(self):self.assertEqual(_norm('Nocturnal Animals!'),'nocturnalanimals')
 def test_unique_local(self):
  idx={'x':{'title':'Nocturnal Animals','year':2016,'imdb_id':'tt4550098'}}
  self.assertEqual(find_local('Nocturnal Animals',2016,idx)['imdb_id'],'tt4550098')
 def test_wrong_year(self):
  idx={'x':{'title':'Heat','year':1995,'imdb_id':'x'}}
  self.assertIsNone(find_local('Heat',1986,idx))
 def test_ambiguous(self):
  idx={'x':{'title':'Crash','year':1996},'y':{'title':'Crash','year':1996}}
  self.assertIsNone(find_local('Crash',1996,idx))
 def test_rejection(self):
  self.assertEqual(rejection_class(['Unknown Movie. Unable to match to existing movie in Library using release title.']),'unknown_movie')
if __name__=='__main__':unittest.main()
