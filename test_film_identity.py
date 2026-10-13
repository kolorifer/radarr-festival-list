import unittest
from unittest.mock import patch
import film_identity as fi
import backcatalog_resolve as resolver

class IdentityTests(unittest.TestCase):
    def test_known_morte_rouge_override(self):
        got = resolver.imdb_lookup("La Morte rouge", 2006)
        self.assertEqual(("tt0806125", "La Morte rouge", 2006), got)

    def test_porte_rouge_rejected(self):
        source = {"title": "La Morte rouge", "year": 2006, "director": "Erice, Víctor", "runtime": 32}
        candidate = {"title": "La Porte Rouge", "year": 2007}
        self.assertFalse(fi.accepts(source, candidate))
        with patch.object(resolver, "fetch_json_with_retry") as fetch:
            self.assertEqual("tt0806125", resolver.imdb_lookup("La Morte rouge", 2006)[0])
            fetch.assert_not_called()

    def test_fuzzy_conflicting_director_runtime(self):
        source = {"title": "Spider", "year": 2002, "director": "Cronenberg, David", "runtime": 98}
        metadata = {"directors": ["Sam Raimi"], "runtime": 121}
        self.assertFalse(fi.accepts(source, {"title": "Spider-Man", "year": 2002}, metadata))
        self.assertEqual(["director_conflict", "runtime_conflict"], fi.supporting_conflicts(source, metadata))

    def test_exact_common_title_cannot_hide_director_conflict(self):
        source = {"title": "Time", "year": 2020, "director": "Bradley, Garrett", "runtime": 81}
        metadata = {"directors": ["Ricky Ko"], "runtime": 99}
        self.assertFalse(fi.accepts(source, {"title": "Time", "year": 2021}, metadata))

    def test_year_tolerance_needs_corroboration(self):
        source = {"title": "Moolaadé", "year": 2004, "director": "Sembene, Ousmane", "runtime": 120}
        candidate = {"title": "Moolaadé", "year": 2003}
        self.assertFalse(fi.accepts(source, candidate))
        self.assertTrue(fi.accepts(source, candidate, {"directors": ["Ousmane Sembene"], "runtime": 120}))

    def test_common_title_requires_metadata(self):
        source = {"title": "Her", "year": 2013, "director": "Jonze, Spike", "runtime": 126}
        self.assertFalse(fi.accepts(source, {"title": "Her", "year": 2013}))
        self.assertTrue(fi.accepts(source, {"title": "Her", "year": 2013},
                                   {"directors": ["Spike Jonze"], "runtime": 126}))

    def test_alias_must_be_explicit_and_cannot_override_conflict(self):
        source = {"title": "Notre musique", "year": 2004, "director": "Godard, Jean-Luc", "runtime": 80}
        candidate = {"title": "Our Music", "year": 2004}
        metadata = {"directors": ["Jean-Luc Godard"], "runtime": 80}
        self.assertFalse(fi.accepts(source, candidate, metadata))
        self.assertTrue(fi.accepts(source, candidate, metadata, aliases=("Our Music",)))
        self.assertFalse(fi.accepts(source, candidate, {"directors": ["Somebody Else"], "runtime": 80}, aliases=("Our Music",)))

    def test_ranked_resolver_rejects_fuzzy_suggestion(self):
        import evidence_sources as es
        with patch.object(es.requests,"get") as get:
            get.return_value.json.return_value={"d":[{"id":"tt4698742","l":"La Porte Rouge","y":2021,"qid":"movie"}]}
            self.assertIsNone(es.imdb_lookup("La Morte rouge",2020))

    def test_source_rank_survives_known_correction(self):
        import backcatalog as bc
        row={"rank":509,"title":"La Morte rouge","year":2006,"director":"Erice, Víctor","runtime":32,"country":"Spain"}
        film,unresolved=bc.resolve_one(row)
        self.assertIsNone(unresolved)
        self.assertEqual("tt0806125",film["imdb_id"])
        self.assertEqual(509,film["tspdt_rank"])
        self.assertEqual(["TSPDT 21st-century #509"],film["signals"])
        self.assertEqual("La Morte rouge",film["source_title"])

    def test_multiple_director_names(self):
        self.assertTrue(fi.director_matches("Dardenne, Jean-Pierre & Luc Dardenne",
                                            ["Jean-Pierre Dardenne", "Luc Dardenne"]))
        self.assertFalse(fi.director_matches("Dardenne, Jean-Pierre & Luc Dardenne", ["Luc Dardenne"]))

    def test_country_conflict(self):
        self.assertIn("country_conflict", fi.supporting_conflicts(
            {"country": "Spain"}, {"countries": ["United States of America"]}))

if __name__ == "__main__":
    unittest.main()
