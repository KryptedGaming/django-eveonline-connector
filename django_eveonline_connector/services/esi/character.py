from django_eveonline_connector.models import EveClient, EveToken
import logging

logger = logging.getLogger(__name__)

def get_eve_character_skillpoints(character_id):
    token = EveToken.objects.get(evecharacter__external_id=character_id)
    skillpoints_response = EveClient.call('get_characters_character_id_skills', token, character_id=character_id)

    return skillpoints_response['total_sp']
    
def get_eve_character_net_worth(character_id):
    token = EveToken.objects.get(evecharacter__external_id=character_id)
    wallet_response = EveClient.call('get_characters_character_id_wallet', token, character_id=character_id)
    return wallet_response