import unittest

from critics_choice_experiment import archive_links, parse_best_picture_page, resolve_record


class CriticsChoiceExperimentTests(unittest.TestCase):
    def test_archive_links_keeps_2001_plus_and_two_2016_pages(self):
        html = """
        <a href='/5th-annual-critics-choice-awards-list-of-nominees-and-winners-2000/'>2000</a>
        <a href='/6th-annual-critics-choice-awards-list-of-nominees-and-winners-2001/'>2001</a>
        <a href='/21st-annual-critics-choice-awards-list-of-nominees-and-winners-2016/'>2016a</a>
        <a href='/22nd-annual-critics-choice-awards-list-of-nominees-and-winners-2016/'>2016b</a>
        """
        links = archive_links(html)
        self.assertEqual([row["ceremony_year"] for row in links], [2001, 2016, 2016])

    def test_best_picture_parser_marks_bold_winner_and_deduplicates(self):
        html = """
        <article><div class='entry-content'>
        <p>FILM CATEGORIES<br>BEST PICTURE<br>Film A<br>Film B<br><strong>Film B</strong><br>Film C</p>
        <p>BEST DIRECTOR<br><strong>Director X – Film B</strong></p>
        </div></article>
        """
        rows = parse_best_picture_page(html, 2020, "https://example.test/2020")
        by_title = {row["title"]: row for row in rows}
        self.assertEqual(set(by_title), {"Film A", "Film B", "Film C"})
        self.assertFalse(by_title["Film A"]["winner"])
        self.assertTrue(by_title["Film B"]["winner"])
        self.assertEqual(by_title["Film B"]["film_year_hint"], 2019)

    def test_december_ceremony_can_resolve_same_year_film(self):
        record = {"title": "Arrival", "film_year_hint": 2015}
        index = {"arrival": [{"imdb_id": "tt2543164", "title": "Arrival", "year": 2016}]}
        row = resolve_record(record, index)
        self.assertEqual(row["imdb_id"], "tt2543164")

    def test_ambiguous_title_is_not_guessed(self):
        record = {"title": "Same", "film_year_hint": 2019}
        index = {"same": [
            {"imdb_id": "tt1", "title": "Same", "year": 2019},
            {"imdb_id": "tt2", "title": "Same", "year": 2019},
        ]}
        self.assertIsNone(resolve_record(record, index))


if __name__ == "__main__":
    unittest.main()
