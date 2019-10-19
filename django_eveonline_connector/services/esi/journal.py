from django_eveonline_connector.models import EveClient, EveToken
from django_eveonline_connector.services.esi.universe import resolve_ids_with_types
import logging

logger = logging.getLogger(__name__)


def get_eve_character_journal(character_id, ignore_ids=[]):
    token = EveToken.objects.get(evecharacter__external_id=character_id)
    journal_response = []
    response = EveClient.call_raw(
        'get_characters_character_id_wallet_journal', token, character_id=character_id)
    journal_response += response.data

    # pull extra journal pages
    total_pages = int(response.header['X-Pages'][0])
    if total_pages > 1:
        for page in range(2, total_pages):
            response = EveClient.call_raw(
                'get_characters_character_id_wallet_journal', token, character_id=character_id, page=page)
            journal_response += response.data

    # clean journal of ignored ids, resolve unknown IDs
    journal = []
    ids_to_resolve = set()
    for entry in journal_response:
        if entry['id'] in ignore_ids:
            logger.debug("Skipping entry %s from journal query" % entry['id'])
            continue
        if 'first_party_id' in entry:
            ids_to_resolve.add(entry['first_party_id'])
        if 'second_party_id' in entry:
            ids_to_resolve.add(entry['second_party_id'])
        journal.append(entry)

    # return empty journal
    print(journal)
    if len(journal) == 0:
        return journal

    resolved_ids = resolve_ids_with_types(ids_to_resolve)

    # resolve ids
    for entry in journal:
        if 'first_party_id' in entry:
            entry['first_party_name'] = resolved_ids[entry['first_party_id']]['name']
            entry['first_party_type'] = resolved_ids[entry['first_party_id']
                                                     ]['type'].upper()
        if 'second_party_id' in entry:
            entry['second_party_name'] = resolved_ids[entry['second_party_id']]['name']
            entry['second_party_type'] = resolved_ids[entry['second_party_id']
                                                      ]['type'].upper()

    return journal
