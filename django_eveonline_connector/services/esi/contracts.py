from django_eveonline_connector.models import EveClient, EveToken
from django_eveonline_connector.services.esi.universe import resolve_ids_with_types
from django_eveonline_connector.services.static.utilities import resolve_type_id_to_type_name
import logging

logger = logging.getLogger(__name__)


def get_eve_character_contracts(character_id, contract_ids_to_ignore=[]):
    logger.info("Getting contracts for %s" % character_id)
    token = EveToken.objects.get(evecharacter__external_id=character_id)
    logger.debug("Resolved ID %s to character %s" %
                 (character_id, token.evecharacter.name))
    # resolve and clean asset list
    contracts_response = EveClient.call(
        'get_characters_character_id_contracts', token, character_id=character_id)
    logger.debug("Response: %s" % contracts_response[0])
    logger.debug("Obtaining IDs found in contracts of %s" %
                 token.evecharacter.name)
    ids_to_resolve = set()
    for contract in contracts_response:
        if 'assignee_id' in contract:
            ids_to_resolve.add(contract['assignee_id'])
        if 'acceptor_id' in contract:
            ids_to_resolve.add(contract['acceptor_id'])
        if 'issuer_id' in contract:
            ids_to_resolve.add(contract['issuer_id'])

    logger.debug("Resolving IDs to names: %s" % ids_to_resolve)
    resolved_ids = resolve_ids_with_types(list(ids_to_resolve))
    logger.debug("Resolved IDs: %s" % resolved_ids)

    contracts = []
    logger.info("Building contract list of %s from ESI response" %
                token.evecharacter.name)
    for contract in contracts_response:
        if contract['contract_id'] in contract_ids_to_ignore:
            continue
        resolved_contract = {
            "contract_id": contract['contract_id'],
            "issued_by": resolved_ids[contract['issuer_id']]['name'],
            "issued_by_type": resolved_ids[contract['issuer_id']]['type'],
            "date_created": contract['date_issued'],
            "contract_type": contract['type'],
            "contract_status": contract['status'].replace("_", " ").upper()
        }

        if 'assignee_id' in contract:
            if contract['assignee_id'] != 0:
                resolved_contract['issued_to'] = resolved_ids[contract['assignee_id']]['name']
                resolved_contract['issued_to_type'] = resolved_ids[contract['assignee_id']]['type']
            else:
                resolved_contract['issued_to'] = None
                resolved_contract['issued_to_type'] = None

        if 'acceptor_id' in contract:
            if contract['acceptor_id'] != 0:
                resolved_contract['accepted_by'] = resolved_ids[contract['acceptor_id']]['name']
                resolved_contract['accepted_by_type'] = resolved_ids[contract['acceptor_id']]['type']
            else:
                resolved_contract['accepted_by'] = None
                resolved_contract['accepted_by_type'] = None

        if 'price' in contract:
            resolved_contract['contract_value'] = contract['price']
        elif 'reward' in contract:
            resolved_contract['contract_value'] = contract['reward']
        else:
            resolved_contract['contract_value'] = 0

        resolved_contract['items'] = get_contract_items(
            character_id, contract['contract_id'])

        contracts.append(resolved_contract)

    return contracts


def get_contract_items(character_id, contract_id):
    logger.info("Getting contract items for %s" % contract_id)
    token = EveToken.objects.get(evecharacter__external_id=character_id)

    contracts_response = EveClient.call(
        'get_characters_character_id_contracts_contract_id_items', token, character_id=character_id, contract_id=contract_id)

    items = []
    for item in contracts_response:
        items.append("%s %s" % (
            item['quantity'], resolve_type_id_to_type_name(item['type_id'])))

    return items
