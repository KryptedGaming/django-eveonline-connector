from django_eveonline_connector.models import EveClient, EveToken
from django_eveonline_connector.services.static.utilities import resolve_type_id_to_type_name
from django_eveonline_connector.services.esi.universe import resolve_ids_with_types
import logging

logger = logging.getLogger(__name__)

def get_eve_character_transactions(character_id, ignore_ids=[]):
    logger.info("Getting transactions for %s" % character_id)
    logger.debug("Transactions to ignore: %s" % ignore_ids)
    token = EveToken.objects.get(evecharacter__external_id=character_id)
    logger.debug("Resolved ID %s to character %s" % (character_id, token.evecharacter.name))
    # resolve and clean transaction list
    transactions_response = EveClient.call('get_characters_character_id_wallet_transactions', token, character_id=character_id)

    # resolve ids 
    ids_to_resolve = set()
    for transaction in transactions_response:
        ids_to_resolve.add(transaction['client_id'])
    resolved_ids = resolve_ids_with_types(ids_to_resolve)

    transactions = []
    for transaction in transactions_response:
        if transaction['transaction_id'] in ignore_ids:
            logger.debug("Skipping ignored transaction: %s" % transaction['transaction_id'] )
            continue
        transaction['client'] = resolved_ids[transaction['client_id']]['name']
        transaction['client_id'] = transaction['client_id']
        transaction['client_type'] = resolved_ids[transaction['client_id']]['type']
        transaction['type_name'] = resolve_type_id_to_type_name(transaction['type_id'])
        transactions.append(transaction)
    logger.debug("Total transactions: %s \n Returned Transactions: %s" % (len(transactions_response), len(transactions)))
    return transactions
