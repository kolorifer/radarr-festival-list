"""Invented source transport only; no real network or credentials."""
import unittest
from unittest.mock import patch
from automation.seedbox_host_io import _get,SourceFailure

class HostSourceTests(unittest.TestCase):
    def fetch(self,status=200,headers=None,chunks=(b'a',),url='https://www.torrentleech.org/torrent/123'):
        with patch('requests.Session') as factory:
            session=factory.return_value.__enter__.return_value
            response=session.get.return_value.__enter__.return_value
            response.status_code=status
            response.headers=headers or {'Content-Type':'text/html'}
            response.iter_content.return_value=iter(chunks)
            result=_get(url,cookies={'invented':'fixture'})
            response.iter_content.assert_called_once_with(1)
            self.assertFalse(session.trust_env)
            self.assertFalse(session.get.call_args.kwargs['allow_redirects'])
            return result

    def test_exact_source_body(self):
        self.assertEqual(self.fetch()[0],b'a')

    def test_finite_reasons_and_retry_after(self):
        for status,reason,owner in [(401,'source_auth_denied',True),(403,'source_auth_denied',True),(404,'source_missing',True),(302,'source_redirect',True),(429,'source_rate_limited',False),(503,'source_temporary',False)]:
            with self.subTest(status=status),self.assertRaises(SourceFailure) as caught:
                self.fetch(status,{'Retry-After':'7200'})
            self.assertEqual(caught.exception.reason,reason)
            self.assertEqual(caught.exception.owner_action,owner)
            if status in (429,503):self.assertEqual(caught.exception.retry_after,7200)

    def test_content_refusal(self):
        with self.assertRaisesRegex(SourceFailure,'source_content_invalid'):
            self.fetch(headers={'Content-Type':'application/octet-stream'})

    def test_wrong_origin_refuses_before_session(self):
        with patch('requests.Session') as factory,self.assertRaisesRegex(ValueError,'host_source_origin'):
            _get('https://www.torrentleech.org/torrent/123/extra',cookies={'invented':'fixture'})
        factory.assert_not_called()

    def test_absolute_timer_interrupts_incomplete_chunk(self):
        import time
        from ai_movie_investigator.responses_http import total_deadline
        def slow():
            time.sleep(.2)
            yield b'x'
        with patch('ai_movie_investigator.responses_http.total_deadline',side_effect=lambda _:total_deadline(.02)):
            with self.assertRaisesRegex(SourceFailure,'source_deadline'):
                self.fetch(chunks=slow())

if __name__=='__main__':unittest.main()
