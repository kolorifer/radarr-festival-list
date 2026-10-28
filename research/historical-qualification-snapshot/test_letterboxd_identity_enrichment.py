import unittest
import letterboxd_identity_enrichment as lb

class LetterboxdIntegrityTests(unittest.TestCase):
    def sample(self):
        return {"@type":"Movie","dateCreated":"2006-02-09","director":[{"name":"Víctor Erice"}],
                "aggregateRating":{"bestRating":5,"ratingValue":3.73,"ratingCount":1118,"reviewCount":224}}

    def test_verified_json_ld_uses_rating_count(self):
        rating,error=lb.verified_rating("tt0806125",self.sample(),{"director":"Erice, Víctor","year":2006},"tt0806125")
        self.assertIsNone(error)
        self.assertEqual(1118,rating["votes"])

    def test_director_and_imdb_identity_required(self):
        for html,dir in [("tt4698742","Erice, Víctor"),("tt0806125","Other, Director")]:
            rating,error=lb.verified_rating("tt0806125",self.sample(),{"director":dir,"year":2006},html)
            self.assertIsNone(rating)
            self.assertEqual("identity_not_corroborated",error)

    def test_unsupported_scale_or_missing_count_remains_missing(self):
        for change in [{"bestRating":10},{"ratingCount":None}]:
            movie=self.sample();movie["aggregateRating"].update(change)
            rating,error=lb.verified_rating("tt0806125",movie,{"director":"Erice, Víctor","year":2006},"tt0806125")
            self.assertIsNone(rating)

    def test_json_ld_comment_wrapper(self):
        html='<script type="application/ld+json">/* <![CDATA[ */{"@type":"Movie","name":"La Morte rouge"}/* ]]> */</script>'
        self.assertEqual("La Morte rouge",lb.structured_movie(html)["name"])

if __name__=="__main__":unittest.main()
