from django_eveonline_connector.models import EveClient, EveToken
from django_eveonline_connector.services.static.utilities import resolve_type_id_to_type_name, resolve_type_id_to_group_id, resolve_group_id_to_category_id, resolve_type_id_to_category_id, resolve_location_id_to_station
import logging

logger = logging.getLogger(__name__)

def resolve_structure_ids(token, structure_ids):
    structure_names = {}
    for structure_id in structure_ids:
        logger.debug("Resolving structure ID: %s" % structure_id)
        structure_response = EveClient.call('get_universe_structures_structure_id', token, structure_id=structure_id)
        if 'error' in structure_response:
            logger.debug("Failed: %s" % structure_response)
            structure_names[structure_id] = "Restricted Structure"
        else:
            structure_names[structure_id] = structure_response.name
    return structure_names