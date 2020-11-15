from django_eveonline_connector.models import EveClient, EveToken
from django_eveonline_connector.exceptions import EveDataResolutionError
from django.core.cache import cache
import logging

logger = logging.getLogger(__name__)

def resolve_id(id):
    return resolve_ids_with_types([95465499, id])[int(id)]

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
    request = EveClient.call('post_universe_names', ids=ids)
    if request.status != 200:
        raise EveDataResolutionError(f"Failed to resolve IDs: {ids}")
    resolved_ids = request.data
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
    response = EveClient.call('get_universe_types_type_id', type_id=type_id, raise_exception=True)
    if response.status != 200:
        raise EveDataResolutionError(
            f"Failed to resolve type_id({type_id}) using ESI. Notify CCP.")
    return response.data

def get_station_id(station_id):
    return EveClient.call('get_universe_stations_station_id', station_id=station_id).data


def get_group_id(group_id):
    return EveClient.call('get_universe_groups_group_id', group_id=group_id).data

def get_category_id(category_id):
    return EveClient.call('get_universe_categories_category_id', category_id=category_id).data

def get_structure_id(structure_id, token_entity_id, safe=True):
    from django_eveonline_connector.models import EveStructure
    if str(structure_id) in cache:
        return cache.get(str(structure_id))

    if safe: # not running safe can lead to ESI lockouts, structure resolution is busted 
        structure = EveStructure.objects.filter(structure_id=structure_id).first()
        if structure:
            return structure.name
        else:
            return "Unknown Structure"
    else:
        try:
            token = EveToken.objects.get(evecharacter__external_id=token_entity_id)
        except EveToken.DoesNotExist:
            raise EveDataResolutionError('Attempted to resolve a structure without a token')

        response = EveClient.call('get_universe_structures_structure_id', token=token, structure_id=structure_id)
        if response.status != 200:
            raise EveDataResolutionError(f"Failed to resolve structure {structure_id} using external ID {token_entity_id}. Reason: {response.data}")

        if cache:
            cache.set(str(structure_id), response.data['name'])
            return response.data['name']
        else:
            return response.data['name']


def get_structure(structure_id, corporation_id):
    from django_eveonline_connector.models import EveCorporation
    corporation = EveCorporation.objects.get(external_id=corporation_id)
    response = EveClient.call(
        'get_universe_structures_structure_id', token=corporation.ceo.token, structure_id=structure_id)
    if response.status != 200:
        raise EveDataResolutionError(
            f"Failed to resolve structure {structure_id} using external ID {corporation_id}. Reason: {response.data}")

    return response
