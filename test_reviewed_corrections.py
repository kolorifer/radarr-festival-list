"""Persistent reviews are retired, including old on-disk approvals."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock,patch
import reviewed_corrections as review

class RetiredReviewTests(unittest.TestCase):
    def test_approve_refused(self):
        with self.assertRaisesRegex(ValueError,'retired'):review.approve({})
    def test_apply_never_reads_or_resolves(self):
        with patch.object(review,'lookup') as lookup:
            resolver=Mock();self.assertIsNone(review.apply({}, {}, {}, {}, resolver))
            lookup.assert_not_called();resolver.assert_not_called()
    def test_revocation_preserves_history(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp).resolve()/'review'
            with review.connection(root,True) as c:c.execute('INSERT INTO decisions VALUES (?,?,?,?)',('old','a'*64,1,json.dumps({})))
            review.revoke('old','Owner retires persistent approval',root)
            with review.connection(root) as c:
                self.assertEqual(c.execute('SELECT count(*) FROM decisions').fetchone()[0],1)
                self.assertEqual(c.execute('SELECT count(*) FROM revocations').fetchone()[0],1)
    def test_old_actions_fail_closed(self):
        import movie_intel_service as svc
        self.assertFalse(svc.reviewed_action_current({'movie':{'identity_source':'owner_reviewed_source'}}))
        self.assertFalse(svc.reviewed_action_current({'movie':{'identity_review':{'decision_id':'old'}}}))
        self.assertTrue(svc.reviewed_action_current({'movie':{'identity_status':'verified_tmdb'}}))
