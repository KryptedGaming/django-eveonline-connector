from django_eveonline_connector.models import EveClient, EveToken
from django_eveonline_connector.services.static.utilities import resolve_type_id_to_type_name, resolve_type_id_to_group_id, resolve_group_id_to_category_id, resolve_type_id_to_category_id, resolve_location_id_to_station
from django_eveonline_connector.services.esi.structures import resolve_structure_ids
import logging

logger = logging.getLogger(__name__)

def get_eve_character_clones(character_id):
    token = EveToken.objects.get(evecharacter__external_id=character_id)
    # resolve and clean asset list
    clones_response = EveClient.call('get_characters_character_id_clones', token, character_id=character_id)
    structure_ids = []
    clones = []
    implant_list = {}
    # get structure ids and build implant list
    for clone in clones_response['jump_clones']:
        if clone['location_type'] == 'structure':
            structure_ids.append(clone['location_id'])
        for implant in clone['implants']:
            implant_list[implant] = {
                "item_id": implant,
                "item_name": resolve_type_id_to_type_name(implant)
            }

    structure_names = resolve_structure_ids(token=token, structure_ids=structure_ids)
    
    # build read-able clone list
    for clone in clones_response['jump_clones']:
        readable_clone = {
            'location': None,
            'implants': [],
        }

        # resolve locaton
        if clone['location_type'] == 'station':
            readable_clone['location'] = resolve_location_id_to_station(clone['location_id'])
        elif clone['location_type'] == 'structure':
            readable_clone['location'] = structure_names[clone['location_id']]
        else:
            readable_clone['location'] = "Unknown Location"
        
        # resolve implants
        for implant in clone['implants']:
            readable_clone['implants'].append(implant_list[implant]['item_name']) # TODO: refactor

        clones.append(readable_clone)
   
    return clones