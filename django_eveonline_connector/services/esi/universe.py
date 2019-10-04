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


def get_type_id(type_id):
    return EveClient.call('get_universe_types_type_id', token=None, type_id=type_id)


def get_station_id(station_id):
    return EveClient.call('get_universe_stations_station_id', token=None, station_id=station_id)


def get_group_id(group_id):
    return EveClient.call('get_universe_groups_group_id', token=None, group_id=group_id)
