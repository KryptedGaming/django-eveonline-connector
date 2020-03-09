from django_eveonline_connector.models import EveClient, EveToken
from django.core.cache import caches
import logging

logger = logging.getLogger(__name__)

def resolve_ids(ids):
    resolved_ids = EveClient.call('post_universe_names', ids=ids).data 
    response = {}
    for resolved_id in resolved_ids:
        external_id = resolved_id['id']
        external_name = resolved_id['name']
        if external_id not in response:
            response[external_id] = external_name
    return response

def resolve_names(names):
    resolved_ids = EveClient.call('post_universe_ids', names=names).data
    return resolved_ids


def resolve_ids_with_types(ids):
    resolved_ids = EveClient.call('post_universe_names', ids=ids).data
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


def get_type_id(type_id):
    try:
        response = EveClient.call('get_universe_types_type_id', type_id=type_id, raise_exception=True)
        return response.data['name']
    except Exception as e:
        logger.error("Failed to resolve type_id(%s) using ESI. Notify CCP.")
        return None 


def get_station_id(station_id):
    return EveClient.call('get_universe_stations_station_id', station_id=station_id).data


def get_group_id(group_id):
    return EveClient.call('get_universe_groups_group_id', group_id=group_id).data

def get_category_id(category_id):
    return EveClient.call('get_universe_categories_category_id', category_id=category_id).data

def get_structure_id(structure_id, token_entity_id):
    try:
        cache = caches['eve_structure_cache']
    except Exception as e:
        cache = None 
        logger.warning("Attempted to use cache 'eve_structure_cache' but it does not exist. Define for performance improvement.")
    
    if cache and str(structure_id) in cache:
        return cache.get(str(structure_id))

    try:
        token = EveToken.objects.get(evecharacter__external_id=token_entity_id)
    except EveToken.DoesNotExist:
        logger.warning(e)
        return "Unknown Structure"

    response = EveClient.call('get_universe_structures_structure_id', token=token, structure_id=structure_id)
    if 'error' in response.data:
        return "Restricted Structure"
    else:
        if cache:
            cache.set(str(structure_id), response.data['name'])
            return response.data['name']
        else:
            return response.data['name']
