"""Initial receipt ownership is assessment evidence, never permission to edit."""
import copy,json,time
from ai_movie_investigator.contracts import require,digest
from identity_triage_intake import normalize
from automation.reviewed_telegram_operator import _row,_target,original_quiescent

KIND='seedbox_assessment_original_ownership_v1'


def target(connection,version,sources):
    row=_row(connection,version)
    require(row['payload'] is not None and row['refs'] is not None,'telegram_original_incomplete')
    payload=json.loads(row['payload']);refs=json.loads(row['refs'])
    require(type(payload) is dict and payload.get('_retry_original_event')==1 and type(refs) is list and len(refs)==1,'telegram_single_original_required')
    ref=refs[0]
    require(type(ref) is dict and set(ref)=={'chat_id','message_id','kind'} and type(ref['chat_id']) is str and type(ref['message_id']) is int and ref['message_id']>0 and ref['kind'] in ('text','caption'),'telegram_original_ref')
    observation=json.loads(row['job_body'])['observation'];original=normalize(observation,sources,'outcome')
    require(not original.get('reason') and original['metadata']['release_key_basis']=='external_id','telegram_source_binding')
    release=payload['data']['release'];job_release=observation['data']['release']
    require(all(release.get(k)==job_release.get(k) for k in ('type','protocol','title','year','name','external_id','meta_imdb','meta_tmdb')) and
        all(payload['data']['indexer'].get(k)==observation['data']['indexer'].get(k) for k in ('identifier','name')),'telegram_original_payload_changed')
    # Normalize retained identity inputs using only the job's transport envelope.
    # No terminal context is manufactured or written to the original database.
    bound=copy.deepcopy(observation);bound['data']['release']=dict(release,implementation=job_release.get('implementation'))
    bound['data']['indexer']=payload['data']['indexer'];checked=normalize(bound,sources,'outcome')
    require(not checked.get('reason') and checked['metadata']==original['metadata'] and checked['release']==original['release']==row['job_source'] and digest([original['release'],original['metadata']])==version,'telegram_source_binding')
    require(row['state'] in ('waiting','edited') and row['job_state'] in ('pending','leased','done','review') and row['job_reason']!='superseded','original_wait_invalid_lifecycle')
    others=connection.execute('select version,refs from retry_messages where refs is not null limit 10001').fetchall()
    require(len(others)<=10000,'telegram_receipt_capacity')
    for other,raw in others:
        if other==version:continue
        for item in json.loads(raw):require((str(item.get('chat_id')),item.get('message_id'))!=(ref['chat_id'],ref['message_id']),'telegram_duplicate_original_ref')
    pin=dict(kind=KIND,version=version,case_id='outcome-'+original['release'],ref=ref,
        payload_sha256=digest(payload),job_body_sha256=digest(json.loads(row['job_body'])),metadata=original['metadata'])
    return dict(row=row,ref=ref,case_id=pin['case_id'],ownership_pin=pin,row_sha256=digest(row))


def pin(binding,config):
    return dict(binding['target']['ownership_pin'],actor_database_sha256=digest(config['actor_database']),actor_selection_sha256=digest(config['sender']))


def completed(connection,selected,config):
    require(selected['kind']==KIND and selected['actor_database_sha256']==digest(config['actor_database']) and selected['actor_selection_sha256']==digest(config['sender']),'ownership_selection_changed')
    actual=target(connection,selected['version'],config['sources'])
    require(dict(actual['ownership_pin'],actor_database_sha256=selected['actor_database_sha256'],actor_selection_sha256=selected['actor_selection_sha256'])==selected,'ownership_changed')
    full=_target(connection,selected['version'],config['sources']);original_quiescent(full['row'],time.time())
    return dict(version=selected['version'],row_sha256=full['row_sha256'],ref=full['ref'],case_id=full['case_id'])
