"""Versioned delegated promotional-credit arithmetic; no provider or credential I/O.

A real observed balance is retained with its original timestamp. A separately
accepted finite delegation permits serial reservations after that observation;
this does not claim the balance was refreshed or control unrelated API clients.
Main must verify exclusive allocation/cutover and all prior uncertain debits.
"""
from fractions import Fraction
from ai_movie_investigator.contracts import shape,require,stamp,hash_id


def amount(value):
    require(type(value) is list and len(value)==2 and all(type(x) is int for x in value) and value[0]>=0 and value[1]>0,'host_credit_amount')
    return Fraction(*value)


def validate(policy,*,now):
    shape(policy,'kind model_profile project account_reference observed_at balance_usd credit_expires_at delegated_at expires_at delegated_usd prior_reserved_usd other_allocated_usd balance_evidence_sha256 prior_history_sha256 prior_credit_sha256 exclusive_cutover_reference paid_fallback')
    from ai_movie_investigator.credit_test import MINI_PROFILE
    require(policy['model_profile']==MINI_PROFILE,'host_credit_model_profile')
    require(policy['kind']=='seedbox_delegated_credit_v1' and policy['paid_fallback'] is False,'host_credit_policy')
    require(type(policy['project']) is str and policy['project'].startswith('proj_') and type(policy['account_reference']) is str and 0<len(policy['account_reference'])<=300,'host_credit_account')
    for key in ('balance_evidence_sha256','prior_history_sha256','prior_credit_sha256'):hash_id(policy[key])
    for key in ('observed_at','credit_expires_at','delegated_at','expires_at'):stamp(policy[key])
    require(policy['observed_at']<=policy['delegated_at']<=now<policy['expires_at']<=policy['credit_expires_at'] and policy['delegated_at']-policy['observed_at']<=900,'host_credit_expired')
    require(type(policy['exclusive_cutover_reference']) is str and 0<len(policy['exclusive_cutover_reference'])<=512,'host_credit_cutover')
    balance=amount(policy['balance_usd']);prior=amount(policy['prior_reserved_usd']);other=amount(policy['other_allocated_usd'])
    ceiling=amount(policy['delegated_usd'])
    # Deliberately conservative: preserve historical reservations even if the
    # observed balance may already reflect some settled usage. Never refund an
    # unknown attempt or assume other consumers stopped from a local assertion.
    require(0<ceiling<=balance-prior-other,'host_credit_ceiling')
    return ceiling


def permit(policy,reservations,*,now):
    ceiling=validate(policy,now=now)
    require(type(reservations) is list,'host_credit_reservations')
    total=Fraction(0);seen=set()
    for row in reservations:
        shape(row,'request_sha256 reserved_usd');hash_id(row['request_sha256'])
        require(row['request_sha256'] not in seen,'host_credit_duplicate')
        seen.add(row['request_sha256']);total+=amount(row['reserved_usd'])
    debit=Fraction(15,100);require(total+debit<=ceiling,'host_credit_exhausted')
    return [debit.numerator,debit.denominator]
