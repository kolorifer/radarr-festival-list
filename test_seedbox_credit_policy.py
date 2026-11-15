import copy,unittest
from ai_movie_investigator.credit_test import MINI_PROFILE
from automation.seedbox_credit_policy import validate,permit

class CreditPolicyTests(unittest.TestCase):
 def policy(self):
  return dict(kind='seedbox_delegated_credit_v1',model_profile=copy.deepcopy(MINI_PROFILE),project='proj_fixture',account_reference='fixture-account',observed_at=1000,delegated_at=1100,expires_at=9000,credit_expires_at=10000,balance_usd=[10,1],delegated_usd=[2,1],prior_reserved_usd=[1,1],other_allocated_usd=[2,1],balance_evidence_sha256='a'*64,prior_history_sha256='b'*64,prior_credit_sha256='c'*64,exclusive_cutover_reference='fixture:main-reviewed-cutover',paid_fallback=False)
 def test_original_observation_retained_through_finite_delegation(self):
  p=self.policy();before=copy.deepcopy(p);self.assertEqual(permit(p,[],now=8000),[3,20]);self.assertEqual(p,before)
 def test_no_expiry_extension_or_late_initial_delegation(self):
  p=self.policy()
  with self.assertRaisesRegex(ValueError,'expired'):validate(p,now=9000)
  p['delegated_at']=2000
  with self.assertRaisesRegex(ValueError,'expired'):validate(p,now=3000)
 def test_unknown_reservations_never_refunded(self):
  p=self.policy();rows=[dict(request_sha256='d'*64,reserved_usd=[19,10])]
  with self.assertRaisesRegex(ValueError,'exhausted'):permit(p,rows,now=1200)
  p['delegated_usd']=[8,1]
  with self.assertRaisesRegex(ValueError,'ceiling'):validate(p,now=1200)
 def test_cash_fallback_and_overallocation_refused(self):
  p=self.policy();p['paid_fallback']=True
  with self.assertRaises(ValueError):validate(p,now=1200)
  p=self.policy();p['delegated_usd']=[9,1]
  with self.assertRaisesRegex(ValueError,'ceiling'):validate(p,now=1200)
