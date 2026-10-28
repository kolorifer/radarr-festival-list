import unittest

from audience_discovery import qualifies


class AudienceDiscoveryTests(unittest.TestCase):
    def test_broad_tier(self):
        self.assertEqual(qualifies(7.2, 100_000), "broad")
        self.assertEqual(qualifies(7.6, 500_000), "broad")

    def test_strong_tier(self):
        self.assertEqual(qualifies(7.8, 25_000), "strong")
        self.assertEqual(qualifies(8.0, 50_000), "strong")

    def test_exceptional_tier(self):
        self.assertEqual(qualifies(8.2, 10_000), "exceptional")

    def test_below_gateway_is_rejected(self):
        self.assertIsNone(qualifies(7.1, 1_000_000))
        self.assertIsNone(qualifies(7.7, 99_999))
        self.assertIsNone(qualifies(8.1, 24_999))
        self.assertIsNone(qualifies(None, 100_000))


if __name__ == "__main__":
    unittest.main()
