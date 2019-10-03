from django_eveonline_connector.models import EveClient, EveToken
from django_eveonline_connector.services.static.utilities import (resolve_type_id_to_type_name, 
    resolve_type_id_to_group_id, resolve_group_id_to_category_id, 
    resolve_type_id_to_category_id, resolve_location_id_to_station)
import logging

logger = logging.getLogger(__name__)
BAD_ASSET_CATEGORIES = [42, 43]

def get_eve_character_assets(character_id):
    logger.info("Gathering token for %s" % character_id)
    token = EveToken.objects.get(evecharacter__external_id=character_id)
    logger.info("Pulling assets of %s" % token.character.name)
    # resolve and clean asset list
    assets = EveClient.call('get_characters_character_id_assets', token, character_id=character_id)
    # purge items not in hangars or asset safety
    logger.debug("Removing assets not in Hangar or AssetSafety")
    assets = [ asset for asset in assets if not asset['location_flag'] not in ['AssetSafety', 'Hangar']]
    # purge bad asset categories
    logger.debug("Purging bad assets categories: %s" % BAD_ASSET_CATEGORIES)
    assets = [ asset for asset in assets if resolve_type_id_to_category_id(asset['type_id']) not in BAD_ASSET_CATEGORIES]
    structure_ids = set()
    for asset in assets:
        # add item name
        asset['item_name'] = resolve_type_id_to_type_name(asset['type_id'])
        # clean excess fields
        if 'is_blueprint_copy' in asset:
            asset.pop('is_blueprint_copy')
        asset.pop('is_singleton')
        asset.pop('type_id')
        asset.pop('item_id')
        asset.pop('location_flag')
        # get list of structure IDs
        if asset['location_type'] == 'other':
            structure_ids.add(asset['location_id'])

    # get structure ids 
    structure_names = {}
    logger.debug("Resolving structure names for structure IDs: %s"  % structure_ids)
    for structure_id in structure_ids:
        structure_response = EveClient.call('get_universe_structures_structure_id', token, structure_id=structure_id)
        if 'error' in structure_response:
            structure_names[structure_id] = "Restricted Structure"
        else:
            structure_names[structure_id] = structure_response.name

    logger.debug("Resolved structures: %s" % structure_names)

    # clean location names
    for asset in assets:
        try: 
            if asset['location_type'] == 'station':
                asset['location'] = resolve_location_id_to_station(asset['location_id'])
                asset.pop('location_type')
                asset.pop('location_id')
            elif asset['location_type'] == 'other':
                asset['location'] = structure_names[asset['location_id']]
                asset.pop('location_type')
                asset.pop('location_id')
        except Exception as e:
            logger.error("Failed to resolve location for asset: %s" % str(e))

    return assets