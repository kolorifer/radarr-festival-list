"""Whole-field withholding; invented model answers, no private/provider I/O."""
import copy, unittest
from unittest.mock import patch
from ai_movie_investigator import new_case as n, supervised_credit as c
from ai_movie_investigator.contracts import Refusal, digest, text
from ai_movie_investigator.history import FILENAME
import test_captured_provenance as fixture

class ProseRetention(unittest.TestCase):
    def test_exact_public_schema_allows_plain_prose_that_title_policy_refuses(self):
        from ai_movie_investigator.controller import output_schema
        from ai_movie_investigator.responses_protocol import schema_value
        schema=output_schema()['properties']['result']['anyOf'][0]['properties']
        self.assertEqual(schema['rationale'],{'type':'string'})
        for value in ('title/year matches','Which edition?','No password is needed','écriture — Łódź 日本語'):
            schema_value(value,schema['rationale'])
        with self.assertRaisesRegex(Refusal,'unsafe_text'):text('title/year matches',600)

    def test_finite_field_predicates_without_raw_retention(self):
        cases=[('ordinary title/year prose','path_or_url_syntax'),('Which edition?','markup_or_reserved_punctuation'),
            ('No password is supplied','credential_label_or_syntax'),('token: invented','credential_label_or_syntax'),
            ('x'*49,'opaque_reference'),('word '*121,'length'),('','empty'),('left\u202eright','unicode_control'),
            ('line\nline','unicode_control'),('https://invented.invalid/item','path_or_url_syntax'),
            ('/Users/invented/private','path_or_url_syntax'),('a@example.invalid','markup_or_reserved_punctuation')]
        for value,reason in cases:
            with self.subTest(reason=reason,value=value):
                answer={'result':{'rationale':value,'uncertainty':'Identity remains unverified.'}}
                retained,flags=n._captured_prose_copy(answer)
                self.assertEqual(retained['result']['rationale'],n._WITHHELD_PROSE)
                self.assertEqual(flags['rationale'],dict(status='withheld',predicate=reason))
                self.assertEqual(answer['result']['rationale'],value)
                text(retained['result']['rationale'],600)
        answer={'result':{'rationale':'écriture — Łódź 日本語','uncertainty':'Unverified.'}}
        self.assertEqual(n._captured_prose_copy(answer)[0],answer)
        self.assertEqual(n._captured_prose_copy(answer)[1]['rationale']['status'],'retained')

    def test_connected_report_and_root_only_store_filtered_copy(self):
        x=fixture.CapturedProvenance('test_receipt_correlated_label_completes_valid_answer');x.setUp();self.addCleanup(x.doCleanups)
        f=x.f;reply=copy.deepcopy(f.reply);reply['result'].update(rationale='InventedIdentity/title match?',uncertainty='No password is available.')
        original=digest(reply)
        self.assertEqual(x.real_label_branch(f.response(reply))['status'],'completed')
        report=f.case.read()[-1]['report'];completed=f.root.read()[-1]
        self.assertEqual(report['reply_hash'],original)
        self.assertNotEqual(report['retained_reply_hash'],original)
        self.assertEqual(report['retained_reply_hash'],digest(completed['answer']))
        self.assertEqual(report['assessment'],completed['answer']['result'])
        self.assertEqual(report['prose_handling']['rationale']['status'],'withheld')
        self.assertFalse(report['draft']['sent']);self.assertFalse(report['provider_verified'])
        for p in (f.case.directory/FILENAME,f.f.state/FILENAME):
            raw=p.read_bytes()
            self.assertNotIn(b'InventedIdentity/title',raw);self.assertNotIn(b'No password is available',raw)
        with self.assertRaises(Refusal):n.complete(f.case,digest(f.request),reply,dict(mode='supervised_supplied',chat_reference='no replay'))

    def test_unicode_prose_draft_limit_is_local_withholding(self):
        x=fixture.CapturedProvenance('test_receipt_correlated_label_completes_valid_answer');x.setUp();self.addCleanup(x.doCleanups)
        reply=copy.deepcopy(x.f.reply);reply['result'].update(rationale='映'*600,uncertainty='画'*600)
        text(reply['result']['rationale'],600)
        self.assertEqual(x.real_label_branch(x.f.response(reply))['status'],'completed')
        report=x.f.case.read()[-1]['report'];self.assertEqual(report['reply_hash'],digest(reply))
        self.assertTrue(all(r['predicate']=='draft_byte_limit' for r in report['prose_handling'].values()))
        self.assertLessEqual(len(report['draft']['text'].encode()),4096)
        self.assertEqual(report['retained_reply_hash'],digest(x.f.root.read()[-1]['answer']))

    def test_withheld_prose_does_not_bypass_citation_validation(self):
        x=fixture.CapturedProvenance('test_receipt_correlated_label_completes_valid_answer');x.setUp();self.addCleanup(x.doCleanups)
        reply=copy.deepcopy(x.f.reply);reply['result']['rationale']='unsafe/withheld'
        reply['result']['citations'][0]['evidence_id']='unsupported'
        with self.assertRaisesRegex(Refusal,'unsupported_citation'):x.real_label_branch(x.f.response(reply))
        self.assertFalse(any(r['type']=='new_case_completed' for r in x.f.case.read()))
        self.assertNotIn(b'unsafe/withheld',(x.f.case.directory/FILENAME).read_bytes())

if __name__=='__main__':unittest.main()
