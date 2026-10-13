import unittest
import integrity_rating_enrichment as enrich

class RatingIntegrityTests(unittest.TestCase):
    def test_only_missing_values_are_filled(self):
        existing={"imdb":{"rating":7.4,"votes":10000}}
        incoming={"imdb":{"rating":7.5,"votes":11000},"letterboxd":{"rating":4.0,"votes":5000}}
        merged,added=enrich.safe_merge(existing,incoming)
        self.assertEqual(existing["imdb"],merged["imdb"])
        self.assertEqual(["letterboxd"],added)
        self.assertNotIn("letterboxd",existing)

    def test_invalid_ratings_are_not_invented(self):
        merged,added=enrich.safe_merge({},{"letterboxd":{"rating":4.1,"votes":None}})
        self.assertEqual({},merged)
        self.assertEqual([],added)

    def test_metadata_drops_secrets_and_unknown_title(self):
        data={"imdb_id":"tt0806125","title":"https://example.invalid/?apikey=private",
              "apikey":"private","year":"2006","links":{"secret":"private"}}
        safe=enrich.public_metadata(data,["La Morte rouge"])
        self.assertIsNone(safe["title"])
        self.assertNotIn("private",str(safe))

    def test_metadata_recognizes_only_valid_external_ids(self):
        data={"imdb_id":"https://imdb.invalid/tt0806125","ids":{"imdb":"tt0806125","secret":"credential"},
              "title":"La Morte Rouge","year":2006,"type":"short"}
        safe=enrich.public_metadata(data,["La Morte rouge"])
        self.assertEqual(["tt0806125"],safe["imdb_ids"])
        self.assertTrue(safe["title_matches_expected"])

if __name__=="__main__":unittest.main()
