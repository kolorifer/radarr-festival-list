import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from ai_movie_investigator.contracts import Refusal, digest
from ai_movie_investigator.disclosure import aliases
from ai_movie_investigator.manual_offline import read_packet, rehearse
from ai_movie_investigator.responses_http import HTTPResult
from ai_movie_investigator.responses_replay import simulated_response


def packet():
    return dict(kind='historical_normalized_projection', source_sha256='a'*64,
                source_report_sha256='b'*64, case_id='outcome-'+'c'*64,
                version='d'*64, material_evidence='e'*64,
                title='Example 2026', year=1998, asserted_imdb='tt12345678',
                reported_candidate_tmdb=12345, reason='title_conflict',
                first_observed=1793629799.735184, last_observed=1793630704.271945,
                source_generated_at='2026-11-03 11:14:34 UTC',
                source_acquired_at='2026-11-03 11:31:00 UTC', report_partial=True,
                reported_movie_search='verified_negative_measurement_time_unknown',
                event_id=None, delivery_id=None, captured_bytes=False,
                currentness='unknown', decisions='unknown', identity_approval='unknown', acquisition_approval='unknown')


class ManualOfflineTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.directory = Path(self.tmp.name).resolve()
        self.path = self.directory / 'input.json'
        self.path.write_text(json.dumps(packet()))
        self.path.chmod(0o600)
        self.p, self.sha = read_packet(self.path)
        self.run_dir = self.directory / 'result'
        self.run_dir.mkdir(mode=0o700)

    def run_case(self, **kwargs):
        return rehearse(self.p, self.sha, self.run_dir, ceiling=[1, 2], **kwargs)

    def test_invented_response_is_validated_and_stays_offline(self):
        with patch('socket.socket', side_effect=AssertionError('network forbidden')):
            report = self.run_case()
        self.assertEqual(report['state'], 'validated_simulated_response')
        self.assertEqual(report['result']['status'], 'unresolved')
        self.assertIsNone(report['result']['candidate'])
        self.assertTrue(report['simulation'])
        self.assertFalse(report['live_provider_called'])
        self.assertIn('complete occurrence decisions', report['unknowns'])
        self.assertEqual(report['facts']['reported_candidate_tmdb'], 12345)

    def test_unsupported_identity_is_refused(self):
        run = digest(dict(packet_sha256=self.sha, purpose='offline_rehearsal'))
        reply = dict(binding_hash=aliases(run), kind='final', lookups=[], result=dict(
            status='supported_candidate', candidate=dict(imdb='tt12345678', tmdb=12345),
            alternatives=[], citations=[], rationale='Example', uncertainty='Unknown', next_action='human_review'))
        report = self.run_case(response=simulated_response(reply, 1))
        self.assertEqual(report['state'], 'simulated_response_or_validation_failed')
        self.assertIsNone(report['result'])

    def test_unknown_response_retains_reservation_and_prevents_replay(self):
        report = self.run_case(response=HTTPResult(200, b'{}', 'req_SIMULATED_1'))
        self.assertEqual(report['state'], 'simulated_response_or_validation_failed')
        with self.assertRaisesRegex(Refusal, 'spending_previous_charge_unknown'):
            self.run_case()

    def test_insufficient_simulated_budget_prevents_send(self):
        with patch('ai_movie_investigator.manual_offline.SimulatedHTTP.post', side_effect=AssertionError('sent')):
            with self.assertRaisesRegex(Refusal, 'spending_ceiling'):
                rehearse(self.p, self.sha, self.run_dir, ceiling=[0, 1])

    def test_live_route_refuses_before_any_input_or_network(self):
        proc = subprocess.run([sys.executable, '-m', 'ai_movie_investigator.manual_offline', '--live'],
                              capture_output=True, text=True, timeout=10)
        self.assertEqual(proc.returncode, 2)
        self.assertIn('responses_real_authorization_unimplemented', proc.stderr)

    def test_cli_writes_private_report_and_refuses_existing_history(self):
        cmd = [sys.executable, '-m', 'ai_movie_investigator.manual_offline', '--input', str(self.path),
               '--output-dir', str(self.run_dir)]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        report = self.run_dir / 'report.json'
        self.assertEqual(report.stat().st_mode & 0o777, 0o600)
        self.assertEqual(json.loads(report.read_text())['state'], 'validated_simulated_response')
        history = self.run_dir / 'ai-investigator-v1.jsonl'
        prior = history.read_bytes()
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        self.assertEqual(proc.returncode, 2)
        self.assertIn('rehearsal_directory_not_empty', proc.stderr)
        self.assertEqual(history.read_bytes(), prior)

    def test_missing_occurrence_must_not_be_fabricated(self):
        p = packet()
        p['event_id'] = 'made_up'
        self.path.write_text(json.dumps(p))
        with self.assertRaisesRegex(Refusal, 'normalized_unknowns_required'):
            read_packet(self.path)


if __name__ == '__main__':
    unittest.main()
