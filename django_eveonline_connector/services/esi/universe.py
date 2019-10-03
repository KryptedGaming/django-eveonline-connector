from django_eveonline_connector.models import EveClient, EveToken
import logging

logger = logging.getLogger(__name__)

def resolve_ids(ids):
    resolved_ids = EveClient.call('post_universe_names', token=None, ids=ids)
    response = {}
    for resolved_id in resolved_ids:
        external_id = resolved_id['id'] 
        external_name = resolved_id['name']
        if external_id not in response:
            response[external_id] = external_name
    return response

def resolve_ids_with_types(ids):
    resolved_ids = EveClient.call('post_universe_names', token=None, ids=ids)
    response = {}
    for resolved_id in resolved_ids:
        external_id = resolved_id['id'] 
        external_name = resolved_id['name']
        external_type = resolved_id['category']
        if external_id not in response:
            response[external_id] = {
                "name": external_name,
                "type": external_type
            }
    return response