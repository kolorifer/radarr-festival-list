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

class DuplicateExactMatchTests(unittest.TestCase):
    @staticmethod
    def candidate(tmdb_id, popularity):
        return {
            'id': tmdb_id, 'title': 'The Snowman',
            'original_title': 'The Snowman', 'release_date': '2017',
            'popularity': popularity,
        }

    def assert_selection(self, rows, expected_id, title='The Snowman', year=2017):
        with patch.object(tmdb, '_get', return_value={'results': rows}), \
             patch.object(tmdb, '_details', side_effect=lambda ident: {'tmdb_id': ident}) as details:
            result = tmdb._search_exact(title, year)
        if expected_id is None:
            self.assertIsNone(result)
            details.assert_not_called()
        else:
            self.assertEqual(result, {'tmdb_id': expected_id})
            details.assert_called_once_with(expected_id)

    def test_zero_exact_matches_stay_unresolved(self):
        for rows in ([], [self.candidate(1, 1000)]):
            with self.subTest(rows=rows):
                self.assert_selection(rows, None, title='Another Movie')

    def test_unique_exact_match_does_not_require_popularity(self):
        for popularity in (None, 0, 'invalid'):
            with self.subTest(popularity=popularity):
                self.assert_selection([self.candidate(1, popularity)], 1)
        row = self.candidate(1, 0)
        del row['popularity']
        self.assert_selection([row], 1)

    def test_snowman_large_gap_is_independent_of_result_order(self):
        rows = [self.candidate(372343, 22.9187), self.candidate(922900, 0.9759)]
        for ordered in (rows, rows[::-1]):
            with self.subTest(ids=[row['id'] for row in ordered]):
                self.assert_selection(ordered, 372343)

    def test_near_tie_or_equal_popularity_stay_unresolved(self):
        for top, runner_up in ((22.9187, 22), (22, 22), (0, 0)):
            with self.subTest(top=top, runner_up=runner_up):
                self.assert_selection([self.candidate(1, top), self.candidate(2, runner_up)], None)

    def test_both_absolute_and_relative_leads_are_required(self):
        # Ratio passes but gap fails; gap passes but ratio fails; both at boundary.
        for top, runner_up, expected_id in (
            (1, 0.01, None), (9.99, 0, None), (100, 20, None),
            (19.99, 2, None), (20, 2, 1), (10, 0, 1),
        ):
            with self.subTest(top=top, runner_up=runner_up):
                self.assert_selection([self.candidate(1, top), self.candidate(2, runner_up)], expected_id)

    def test_all_candidates_need_valid_popularity(self):
        for invalid in (None, '100', True, False, -1, float('nan'),
                        float('inf'), float('-inf'), [], {}):
            for index in range(3):
                with self.subTest(invalid=invalid, index=index):
                    rows = [self.candidate(1, 100), self.candidate(2, 1), self.candidate(3, 0)]
                    rows[index]['popularity'] = invalid
                    self.assert_selection(rows, None)
        for index in range(3):
            with self.subTest(missing_index=index):
                rows = [self.candidate(1, 100), self.candidate(2, 1), self.candidate(3, 0)]
                del rows[index]['popularity']
                self.assert_selection(rows, None)

    def test_runner_up_is_strongest_of_all_other_matches(self):
        for runner_up, expected_id in ((1, 1), (19, None)):
            with self.subTest(runner_up=runner_up):
                self.assert_selection([
                    self.candidate(2, 0.01), self.candidate(1, 100),
                    self.candidate(3, runner_up),
                ], expected_id)

    def test_popularity_never_broadens_title_or_year_matching(self):
        top = self.candidate(1, 1000)
        for field, value in (('title', 'The Snowman Returns'), ('release_date', '2018')):
            with self.subTest(field=field):
                row = dict(top, **{field: value})
                if field == 'title':
                    row['original_title'] = value
                self.assert_selection([row, self.candidate(2, 1)], 2)

    def test_normalized_original_title_can_still_match(self):
        row = dict(self.candidate(1, 20), title='Localized title', original_title='THE SNOW-MAN!')
        self.assert_selection([row, self.candidate(2, 1)], 1)

    def test_duplicate_search_without_year_stays_unresolved(self):
        self.assert_selection([self.candidate(1, 100), self.candidate(2, 1)], None, year=None)

    def test_resolve_movie_snowman_and_hamnet_offline(self):
        # Supplied issue evidence for Snowman; synthetic unique Hamnet response.
        # Exercise details compaction and cache with no network transport.
        snowman = [self.candidate(922900, 0.9759), self.candidate(372343, 22.9187)]
        hamnet = [{'id': 858024, 'title': 'Hamnet', 'release_date': '2025'}]

        def fake_get(path, params):
            if path == '/search/movie':
                return {'results': hamnet if params['query'].startswith('Hamnet') else snowman}
            ident = int(path.rsplit('/', 1)[1])
            return next(row for row in hamnet + snowman if row['id'] == ident)

        with tempfile.TemporaryDirectory() as directory, \
             patch.object(tmdb, 'CACHE_PATH', Path(directory) / 'cache.json'), \
             patch.object(tmdb, 'TOKEN', 'synthetic-test-token'), \
             patch.object(tmdb, '_get', side_effect=fake_get) as get:
            self.assertEqual(tmdb.resolve_movie('The Snowman', 2017)['tmdb_id'], 372343)
            self.assertEqual(tmdb.resolve_movie('Hamnet', 2025)['tmdb_id'], 858024)
            self.assertIsNone(tmdb.resolve_movie('Hamnet 2025', 2016))
            get.assert_any_call('/search/movie', {
                'query': 'Hamnet 2025', 'year': 2016, 'include_adult': 'false',
                'language': 'en-US', 'page': 1,
            })
            # Successful identities continue to use the existing cache path.
            get.reset_mock()
            self.assertEqual(tmdb.resolve_movie('The Snowman', 2017)['tmdb_id'], 372343)
            get.assert_not_called()


if __name__=='__main__':unittest.main()
