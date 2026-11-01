"""SIMULATED Responses HTTP proof; static synthetic fixture, no network.

Run explicitly: python -m ai_movie_investigator.responses_replay --synthetic
"""
import argparse
from pathlib import Path
import tempfile

from .contracts import encoded
from .controller import investigate, output_schema
from .history import History
from .replay import NOW, packet_for, simulated_replies
from .responses_http import ExplicitCredential, HTTPResult, SimulatedHTTP, SYNTHETIC_CREDENTIAL
from .responses_protocol import MODEL, OUTPUT_TOKENS
from .responses_transport import ResponsesTransport, SimulatedAuthorization
from .review import daily_digest


def simulated_response(reply, number):
    """Documented selected Responses shape; not evidence of live compatibility."""
    return HTTPResult(200, encoded(dict(
        id='resp_SIMULATED_' + str(number), object='response', status='completed', model=MODEL,
        error=None, incomplete_details=None, store=False, background=False, tools=[], tool_choice='none',
        service_tier='default', prompt_cache_options=dict(ttl='30m'),
        max_output_tokens=OUTPUT_TOKENS,
        text=dict(format=dict(type='json_schema', name='retained_investigator_v1', strict=True, schema=output_schema())),
        output=[dict(id='rs_SIMULATED_' + str(number), type='reasoning', summary=[], encrypted_content='SIMULATED-OPAQUE-NOT-RETAINED'),
                dict(id='msg_SIMULATED_' + str(number), type='message', role='assistant', status='completed',
                     content=[dict(type='output_text', text=encoded(reply).decode(), annotations=[])])],
        usage=dict(input_tokens=1200, input_tokens_details=dict(cached_tokens=0, cache_write_tokens=0,
                   cache_write_tokens_details=dict(ttl_30m_tokens=0, ttl_12h_tokens=0)), output_tokens=300,
                   output_tokens_details=dict(reasoning_tokens=50), total_tokens=1500))),
        'req_SIMULATED_' + str(number))


def simulated_transport(packet, responses=None, **kwargs):
    http = SimulatedHTTP(responses if responses is not None else
                         [simulated_response(r, n) for n, r in enumerate(simulated_replies(packet), 1)])
    return ResponsesTransport(enabled=True, http=http, credential=ExplicitCredential(SYNTHETIC_CREDENTIAL),
                              authorization=SimulatedAuthorization(encoded(packet), NOW-1, NOW+120),
                              clock=lambda: NOW, **kwargs)


def run_responses_synthetic(directory):
    packet = packet_for(1274)
    history = History(directory, clock=lambda: NOW)
    job, _ = history.intake(packet)
    transport = simulated_transport(packet)
    result = investigate(history, job, 'SIMULATED-responses-invocation', transport)
    review = daily_digest(history, selected_date='2026-10-31', timezone='Europe/Warsaw')
    return history, result, review, transport


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--synthetic', required=True, action='store_true')
    parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='SIMULATED-responses-') as tmp:
        _, _, review, _ = run_responses_synthetic(Path(tmp).resolve())
        print('SIMULATED HTTP — no real identification or verified API access\n' + review['text'])


if __name__ == '__main__':
    main()
