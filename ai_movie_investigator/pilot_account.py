"""Single synthetic pilot account with post-effect, fixture-issued observations.

The issuer only models a fixed local fake; it is never live authorization.
Unknown effects retain their reservations and can never be resent or refunded.
"""
import hashlib
import hmac
import secrets
import uuid

from .contracts import decode, digest, encoded, identifier, require, shape
from .spending import pair, rational, POLICY
from .responses_protocol import OUTPUT_TOKENS, response_id, validate_usage

COUNT_ROUTE = '/v1/responses/input_tokens'
COVERAGE = 'entire-canonical-responses-body-including-instructions-schema-v1'


class FixtureIssuer:
    """An independently enrolled fake issuer, not a real provider verifier."""
    def __init__(self, identity):
        self.identity = identifier(identity)
        self._key = secrets.token_bytes(32)
        self._issued = None

    def _issue(self, receipt):
        require(self._issued is None, 'pilot_issuer_already_issued')
        body = encoded(receipt)
        self._issued = (body, hmac.new(self._key, body, hashlib.sha256).hexdigest())
        return dict(receipt=decode(body, 4096), signature=self._issued[1])

    def verify(self, envelope):
        require(type(envelope) is dict and set(envelope) == {'receipt', 'signature'} and
                self._issued is not None, 'pilot_issuer_observation_unknown')
        body = encoded(envelope['receipt'])
        signature = envelope['signature']
        require(isinstance(signature, str) and self._issued == (body, signature) and
                hmac.compare_digest(signature, hmac.new(self._key, body, hashlib.sha256).hexdigest()) and
                envelope['receipt']['issuer'] == self.identity, 'pilot_issuer_observation_unknown')
        return decode(body, 4096)


class FixtureCounter:
    def __init__(self, receipt, issuer_id):
        self.receipt = decode(encoded(receipt), 4096)
        self.requests = []
        self.issuer = FixtureIssuer(issuer_id)

    def count(self, body, *, project, run, local_request_id, expected_request_hash):
        require(not self.requests, 'pilot_count_consumed')
        identifier(local_request_id)
        require(type(body) is bytes and body == encoded(decode(body, 65536)), 'pilot_noncanonical_wire_body')
        request_hash = digest(decode(body, 65536))
        require(request_hash == expected_request_hash, 'pilot_count_body_changed')
        self.requests.append(dict(route=COUNT_ROUTE, request_hash=request_hash,
                                  body=body, project=project, run=run, local_request_id=local_request_id))
        r = dict(self.receipt, issuer=self.issuer.identity, operation='count', local_request_id=local_request_id)
        require(r['request_hash'] == request_hash and r['project'] == project and r['run'] == run, 'pilot_count_receipt_unknown')
        return self.issuer._issue(r)


class PilotAccount:
    def __init__(self, control, selection, counter, model):
        self.control, self.selection, self.counter, self.model = control, selection, counter, model
        self.counter_issuer, self.model_issuer = counter.issuer, model.issuer

    def reserve(self, body, generation_id):
        s, quote = self.selection, self.selection['quote']
        require(type(body) is bytes and body == encoded(decode(body, 65536)), 'pilot_noncanonical_wire_body')
        identifier(generation_id)
        require(quote['policy'] == POLICY and quote['coverage'] == COVERAGE and
                quote['ancillary'] == 'none' and quote['currency'] == 'TEST-USD' and
                quote['output_bound'] == OUTPUT_TOKENS and type(self.counter) is FixtureCounter,
                'pilot_quote_unsupported')
        require(s['ceiling'] is not None and rational(s['ceiling']) > 0, 'pilot_owner_ceiling_missing')
        require(quote['request_hash'] == digest(decode(body, 65536)), 'pilot_quote_body_changed')
        for field in ('input','cache_read','cache_write','output','count_maximum_fee'):
            rational(quote[field])
        maximum_count_fee = rational(quote['count_maximum_fee'])
        require(maximum_count_fee <= rational(s['ceiling']), 'pilot_count_ceiling')
        count_id = 'simulated-count-' + uuid.uuid4().hex
        with self.control.transaction(write=True) as (events, append):
            self._claimed(events)
            require(not any(e['type'] == 'pilot_count_reserved' for e in events), 'pilot_count_consumed')
            append(dict(type='pilot_count_reserved', at=self.control.clock(), run=s['run'], project=s['project'],
                        cost=pair(maximum_count_fee), request_hash=quote['request_hash'], local_request_id=count_id))
        envelope = self.counter.count(body, project=s['project'], run=s['run'], local_request_id=count_id, expected_request_hash=quote['request_hash'])
        require(self.counter.issuer is self.counter_issuer, 'pilot_issuer_changed')
        count = self.counter_issuer.verify(envelope)
        shape(count, 'project run coverage request_hash input_tokens fee known request_id issuer operation local_request_id')
        require(count['known'] is True and count['operation'] == 'count' and count['local_request_id'] == count_id and
                count['issuer'] == s['site_facts']['counter_issuer'] and count['project'] == s['project'] and
                count['run'] == s['run'] and count['request_hash'] == quote['request_hash'] and
                count['coverage'] == COVERAGE and type(count['input_tokens']) is int and
                0 < count['input_tokens'] <= 65536, 'pilot_count_receipt_unknown')
        response_id(count['request_id'])
        require(rational(count['fee']) <= maximum_count_fee, 'pilot_count_fee_unknown')
        with self.control.transaction(write=True) as (events, append):
            self._claimed(events)
            reservations = [e for e in events if e['type'] == 'pilot_count_reserved']
            require(len(reservations) == 1 and reservations[0]['local_request_id'] == count_id and
                    not any(e['type'] == 'pilot_count_settled' for e in events), 'pilot_count_consumed')
            append(dict(type='pilot_count_settled', at=self.control.clock(), run=s['run'],
                        cost=count['fee'], receipt=count, issuer_signature=envelope['signature']))
        maximum = count['input_tokens'] * max(rational(quote[k]) for k in ('input','cache_read','cache_write'))
        maximum += OUTPUT_TOKENS * rational(quote['output'])
        require(maximum + rational(count['fee']) <= rational(s['ceiling']), 'pilot_model_ceiling')
        with self.control.transaction(write=True) as (events, append):
            self._claimed(events)
            require(not any(e['type'] == 'pilot_model_reserved' for e in events), 'pilot_generation_consumed')
            append(dict(type='pilot_model_reserved', at=self.control.clock(), run=s['run'], project=s['project'],
                        request_hash=quote['request_hash'], local_request_id=generation_id, tokens=count['input_tokens'],
                        output_bound=OUTPUT_TOKENS, maximum=pair(maximum), quote=quote))
        return maximum

    def _claimed(self, events, *, current=True):
        claims = [e for e in events if e['type'] == 'pilot_claim']
        require(len(claims) == 1 and claims[0]['selection_hash'] == digest(self.selection), 'pilot_account_claim')
        if current:
            require(self.control.clock() < self.selection['expires_at'], 'pilot_account_expired')

    def send(self, body, local_request_id):
        require(type(body) is bytes and body == encoded(decode(body, 65536)), 'pilot_noncanonical_wire_body')
        with self.control.transaction(write=True) as (events, append):
            self._claimed(events)
            rows = [e for e in events if e['type'] == 'pilot_model_reserved']
            require(len(rows) == 1 and rows[0]['local_request_id'] == local_request_id and
                    rows[0]['request_hash'] == digest(decode(body, 65536)), 'pilot_send_unbound')
            require(not any(e['type'] == 'pilot_model_sent' for e in events), 'pilot_generation_consumed')
            append(dict(type='pilot_model_sent', at=self.control.clock(), run=self.selection['run'],
                        project=self.selection['project'], request_hash=rows[0]['request_hash'], local_request_id=local_request_id))

    def settle(self, accounting, envelope, returned_response_sha256):
        usage = validate_usage(accounting['usage'])
        s = self.selection
        with self.control.transaction(write=True) as (events, append):
            self._claimed(events, current=False)
            require(not any(e['type'] == 'pilot_usage_observed' for e in events), 'pilot_usage_replayed')
            append(dict(type='pilot_usage_observed', at=self.control.clock(), run=s['run'], accounting=accounting))
        require(self.model.issuer is self.model_issuer, 'pilot_issuer_changed')
        receipt = self.model_issuer.verify(envelope)
        shape(receipt, 'project run request_hash request_id response_id known issuer operation local_request_id response_sha256 usage_hash')
        require(receipt['known'] is True and receipt['operation'] == 'generation' and
                receipt['issuer'] == s['site_facts']['model_issuer'] and receipt['project'] == s['project'] and
                receipt['run'] == s['run'] and receipt['request_hash'] == s['quote']['request_hash'] and
                receipt['local_request_id'] == accounting['local_request_id'] and
                receipt['request_id'] == accounting.get('request_id') and
                receipt['response_id'] == accounting['response_id'] and
                receipt['usage_hash'] == digest(accounting['usage']) and
                receipt['response_sha256'] == returned_response_sha256 and
                accounting['request_hash'] == s['quote']['request_hash'] and accounting['policy'] == POLICY,
                'pilot_model_receipt_unknown')
        response_id(receipt['request_id']); response_id(receipt['response_id'])
        q = s['quote']; d = usage['input_tokens_details']
        ordinary = usage['input_tokens'] - d['cached_tokens'] - d['cache_write_tokens']
        cost = (ordinary*rational(q['input']) + d['cached_tokens']*rational(q['cache_read']) +
                d['cache_write_tokens']*rational(q['cache_write']) + usage['output_tokens']*rational(q['output']))
        with self.control.transaction(write=True) as (events, append):
            self._claimed(events, current=False)
            rows = [e for e in events if e['type'] == 'pilot_model_reserved']
            sent = [e for e in events if e['type'] == 'pilot_model_sent']
            counts = [e for e in events if e['type'] == 'pilot_count_settled']
            require(len(rows) == len(sent) == len(counts) == 1 and
                    rows[0]['local_request_id'] == sent[0]['local_request_id'] == receipt['local_request_id'] and
                    counts[0]['receipt']['request_id'] != receipt['request_id'] and
                    usage['input_tokens'] <= rows[0]['tokens'] and cost <= rational(rows[0]['maximum']),
                    'pilot_usage_over_reservation')
            require(not any(e['type'] == 'pilot_model_settled' for e in events), 'pilot_settlement_sequence')
            append(dict(type='pilot_model_settled', at=self.control.clock(), run=s['run'],
                        cost=pair(cost), accounting=accounting, receipt=receipt, issuer_signature=envelope['signature']))
