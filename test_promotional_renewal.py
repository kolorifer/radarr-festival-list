"""Invented append-only successor promotion; never contacts a provider/account."""
import copy,io,time,unittest
from unittest.mock import patch
from contextlib import redirect_stdout
from fractions import Fraction
from ai_movie_investigator import supervised_credit as c
from ai_movie_investigator.contracts import Refusal,digest
from ai_movie_investigator.history import History,FILENAME
from ai_movie_investigator.credit_test import retained_total
from test_standing_credit import StandingTests
from test_supervised_diagnostics import DiagnosticTests

class PromotionalRenewalTests(unittest.TestCase):
 def setUp(self):
  self.f=StandingTests('test_grant_preserves_legacy_hashes_and_default_cap');self.f.setUp();self.addCleanup(self.f.doCleanups)
  self.f.grant();self.before=(self.f.state/FILENAME).read_bytes();self.credits=(self.f.state/'credit'/FILENAME).read_bytes()
  self.now=self.f.e['credit_expires_at']+1
  self.e=dict(self.f.e,observed_at=self.now-1,expires_at=self.now+120,credit_expires_at=self.now+86400,available_usd=[100,1])
  self.selected=self.f.select(self.e)
 def renew(self):
  with patch.object(c.time,'time',return_value=self.now):return c.renew_promotional(self.f.state,self.selected)
 def test_append_preserves_original_and_all_reservations_and_allocates_next(self):
  with patch('socket.socket',side_effect=AssertionError('network')),patch.object(c,'prompt_credential',side_effect=AssertionError('credential')):
   self.assertEqual(self.renew()['next_slot'],7)
   self.assertTrue((self.f.state/FILENAME).read_bytes().startswith(self.before));self.assertEqual((self.f.state/'credit'/FILENAME).read_bytes(),self.credits)
   with patch.object(c.time,'time',return_value=self.now):self.assertEqual(c.prepare_next(self.f.state,self.selected),7)
  rows=History(self.f.state).read();self.assertEqual(rows[20]['credit_expires_at'],self.f.e['credit_expires_at']);self.assertEqual(rows[-2]['promotional_renewal_sha256'],digest(rows[21]));self.f.preserved()
 def test_changed_account_project_policy_cash_stale_or_low_balance_refuse_without_append(self):
  for delta in ({'account_reference':'other'},{'project':'proj_other'},{'paid_fallback':True},{'credit_kind':'purchased'},{'expires_at':self.now-1},{'available_usd':[17,100]},{'credit_expires_at':self.f.e['credit_expires_at']}):
   self.selected=self.f.select(dict(self.e,**delta))
   with self.assertRaises(Refusal):self.renew()
   self.assertEqual((self.f.state/FILENAME).read_bytes(),self.before)
 def test_no_renewal_before_expiry_and_no_duplicate(self):
  with self.assertRaises(Refusal):c.renew_promotional(self.f.state,self.selected)
  self.renew()
  with self.assertRaises(Refusal):self.renew()
 def test_pending_old_attempt_cannot_be_revived(self):
  c.prepare_next(self.f.state,self.f.selected)
  with self.assertRaises(Refusal):self.renew()
  with patch.object(c.time,'time',return_value=self.now),self.assertRaises(Refusal):c.run(self.f.state,self.selected,7)
 def test_old_reservation_corruption_refuses(self):
  with History(self.f.state/'credit').transaction(write=True) as (_,append):append({'type':'corrupt'})
  with self.assertRaises((Refusal,KeyError)):self.renew()
 def test_new_fake_wire_receipt_and_no_replay_after_renewal(self):
  self.renew()
  original=History.__init__
  def fixed_clock(history,directory,clock=None):original(history,directory,clock=lambda:self.now)
  with patch.object(History,'__init__',fixed_clock),patch.object(c.time,'time',return_value=self.now),DiagnosticTests().inputs(),self.f.wire(7),redirect_stdout(io.StringIO()):
   self.assertEqual(c.run(self.f.state,self.selected,None,clock=lambda:self.now)['slot'],7)
  self.assertEqual(retained_total(self.f.credit.read(),'proj_fixture'),Fraction(18,100))
  with patch.object(c.time,'time',return_value=self.now),self.assertRaises(Refusal):c.run(self.f.state,self.selected,7)
  self.f.preserved()

 def test_exact_original_state_binding_checked_under_append_lock(self):
  root=History(self.f.state);rows=root.read();credit=self.f.credit
  expected=dict(root_identity=list(root.identity),root_prefix_sha256=digest(rows),credit_identity=list(credit.identity),credit_file_identity=c.file_identity(credit),credit_sha256=digest(credit.read()),original_grant_sha256=digest(rows[20]))
  for key in expected:
   bad=copy.deepcopy(expected);bad[key]=None
   with patch.object(c.time,'time',return_value=self.now),self.assertRaises(Refusal):c.renew_promotional(self.f.state,self.selected,expected=bad)
   self.assertEqual((self.f.state/FILENAME).read_bytes(),self.before)
  with patch.object(c.time,'time',return_value=self.now):self.assertEqual(c.renew_promotional(self.f.state,self.selected,expected=expected)['next_slot'],7)
