"""Durable SIMULATED token spending. No real rates, counter or authorization.

Uses the investigator's private hash-linked, fsynced history and process lock.
An unsettled reservation permanently blocks this selected run, including after
restart. Only validated, bound usage can release a known unused reservation.
"""
from fractions import Fraction

from .contracts import decode, digest, encoded, require, scope, stamp
from .history import History
from .responses_protocol import INPUT_TOKENS, MODEL, OUTPUT_TOKENS

POLICY = dict(model=MODEL, service_tier='default', prompt_cache_options=dict(ttl='30m'))
COUNTER = 'SIMULATED-complete-request-bytes-v1'
PRICING = dict(identity='SIMULATED-rational-USD-v1', currency='USD',
               input=[4, 1000000], cache_read=[2, 1000000],
               cache_write=[8, 1000000], output=[20, 1000000])


def rational(value):
    require(isinstance(value, list) and len(value) == 2 and
            all(type(x) is int for x in value) and value[0] >= 0 and value[1] > 0,
            'spending_rational')
    return Fraction(*value)


def pair(value):
    return [value.numerator, value.denominator]


class SimulatedSpending:
    """The only admitted counter/rate implementation is this finite fixture.

    A byte is one TEST token, counting the entire serialized selected request,
    instructions and schema. This does not establish a real tokenizer bound.
    No caller callback, custom price, token-count endpoint or default ceiling.
    """
    def __init__(self, history, *, binding, ceiling, expires_at):
        require(type(history) is History, 'spending_history')
        scope(binding)
        self.history = history
        self.spec = dict(binding=binding, ceiling=pair(rational(ceiling)),
                         expires_at=stamp(expires_at), policy=POLICY,
                         pricing=PRICING, counter=COUNTER, synthetic=True)
        self.spec = decode(encoded(self.spec), 8192)
        self.identity = digest(self.spec)
        with history.transaction(write=True) as (events, append):
            prior = [e for e in events if e['type'] == 'spending_open']
            # One selected budget per history, never a new name to bypass it.
            require(not prior or len(prior) == 1 and prior[0]['spec'] == self.spec,
                    'spending_budget_changed')
            if not prior:
                append(dict(type='spending_open', budget=self.identity, spec=self.spec,
                            at=stamp(history.clock())))

    def _rows(self, events):
        require(self.spec['policy'] == POLICY and self.spec['pricing'] == PRICING
                and self.spec['counter'] == COUNTER and self.spec['synthetic'] is True,
                'spending_policy_unknown')
        require(any(e['type'] == 'spending_open' and e['budget'] == self.identity
                    and e['spec'] == self.spec for e in events), 'spending_binding_changed')
        rows = [e for e in events if e.get('budget') == self.identity]
        now = stamp(self.history.clock())
        require(now < self.spec['expires_at'] and
                all(now >= e['at'] for e in rows), 'spending_clock_or_expiry')
        reserved = [e for e in rows if e['type'] == 'spending_reserved']
        settled = [e for e in rows if e['type'] == 'spending_settled']
        return now, reserved, settled

    def reserve(self, body, reservation, binding):
        require(binding == self.spec['binding'], 'spending_case_changed')
        request = decode(body, 65536)
        require(all(request.get(k) == v for k, v in POLICY.items()), 'spending_policy_unknown')
        require(type(body) is bytes and 0 < len(body) <= INPUT_TOKENS,
                'spending_counter_limit')
        require(reservation['request_hash'] == digest(request), 'spending_request_changed')
        tokens = len(body)
        cost = tokens * max(rational(PRICING[k]) for k in ('input', 'cache_read', 'cache_write'))
        cost += OUTPUT_TOKENS * rational(PRICING['output'])
        with self.history.transaction(write=True) as (events, append):
            now, reserved, settled = self._rows(events)
            require(len(reserved) < 2, 'spending_request_limit')
            require(len(reserved) == len(settled), 'spending_previous_charge_unknown')
            require(not any(e['request_hash'] == reservation['request_hash'] or
                            e['local_request_id'] == reservation['local_request_id'] for e in reserved),
                    'spending_request_consumed')
            used = sum((rational(e['cost']) for e in settled), Fraction())
            require(used + cost <= rational(self.spec['ceiling']), 'spending_ceiling')
            record = dict(type='spending_reserved', budget=self.identity, at=now,
                          local_request_id=reservation['local_request_id'],
                          request_hash=reservation['request_hash'], tokens=tokens,
                          output_bound=OUTPUT_TOKENS, cost=pair(cost), synthetic=True)
            append(record)
        return dict(budget=self.identity, reserved=pair(cost), counter=COUNTER,
                    pricing=PRICING['identity'], currency='USD', synthetic=True)

    def before_send(self, body, reservation):
        """Recheck and consume the single send under the durable lock."""
        with self.history.transaction(write=True) as (events, append):
            now, reserved, settled = self._rows(events)
            require(len(reserved) == len(settled) + 1, 'spending_send_sequence')
            row = reserved[-1]
            require(row['request_hash'] == reservation['request_hash'] == digest(decode(body, 65536)) and
                    row['local_request_id'] == reservation['local_request_id'] and
                    row['tokens'] == len(body), 'spending_send_binding')
            require(not any(e['type'] == 'spending_sent' and e['budget'] == self.identity and
                            e['local_request_id'] == row['local_request_id'] for e in events),
                    'spending_send_consumed')
            append(dict(type='spending_sent', budget=self.identity, at=now,
                        local_request_id=row['local_request_id'], request_hash=row['request_hash'], synthetic=True))

    def settle(self, reservation, accounting):
        # parse_response has already validated token totals, partitions, policy
        # and mandatory fields. Revalidate here too: this public method cannot
        # release funds on an arbitrary caller's accounting assertions.
        from .responses_protocol import validate_usage
        usage = validate_usage(accounting['usage'])
        require(accounting['model'] == MODEL and accounting['policy'] == POLICY,
                'spending_policy_unknown')
        require(accounting['local_request_id'] == reservation['local_request_id'] and
                accounting['request_hash'] == reservation['request_hash'], 'spending_receipt_changed')
        details = usage['input_tokens_details']
        ordinary = usage['input_tokens'] - details['cached_tokens'] - details['cache_write_tokens']
        cost = (ordinary * rational(PRICING['input']) +
                details['cached_tokens'] * rational(PRICING['cache_read']) +
                details['cache_write_tokens'] * rational(PRICING['cache_write']) +
                usage['output_tokens'] * rational(PRICING['output']))
        with self.history.transaction(write=True) as (events, append):
            now, reserved, settled = self._rows(events)
            require(len(reserved) == len(settled) + 1, 'spending_settlement_sequence')
            row = reserved[-1]
            require(row['request_hash'] == reservation['request_hash'] and
                    row['local_request_id'] == reservation['local_request_id'], 'spending_receipt_changed')
            require(any(e['type'] == 'spending_sent' and e['budget'] == self.identity and
                        e['local_request_id'] == row['local_request_id'] and
                        e['request_hash'] == row['request_hash'] for e in events), 'spending_send_missing')
            require(not any(e['response_id'] == accounting['response_id'] for e in settled),
                    'spending_response_consumed')
            require(usage['input_tokens'] <= row['tokens'] and
                    usage['output_tokens'] <= row['output_bound'] and cost <= rational(row['cost']),
                    'spending_usage_exceeds_reservation')
            append(dict(type='spending_settled', budget=self.identity, at=now,
                        local_request_id=row['local_request_id'], request_hash=row['request_hash'],
                        response_id=accounting['response_id'], usage=usage, cost=pair(cost), synthetic=True))
