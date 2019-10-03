from django_eveonline_connector.models import EveClient, EveToken
from django_eveonline_connector.services.esi.universe import resolve_ids
import logging

logger = logging.getLogger(__name__)

def get_eve_character_contacts(character_id):
    token = EveToken.objects.get(evecharacter__external_id=character_id)
    # resolve and clean asset list
    contacts_response = EveClient.call('get_characters_character_id_contacts', token, character_id=character_id)
    unresolved_ids = []
    contacts = []
    # get list of ids
    for contact in contacts_response:
        unresolved_ids.append(contact['contact_id'])

    resolved_ids = resolve_ids(unresolved_ids)

    # match ids to contacts 
    for contact in contacts_response:
        contacts.append({
            'name': resolved_ids[contact['contact_id']],
            'external_id': contact['contact_id'],
            'type': contact['contact_type'].upper(),
            'standing': contact['standing'],
        })
    return contacts