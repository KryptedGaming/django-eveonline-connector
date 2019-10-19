from django_eveonline_connector.models import EveClient, EveToken
from django_eveonline_connector.services.static.utilities import (resolve_type_id_to_type_name,
                                                                  resolve_type_id_to_group_id,
                                                                  resolve_type_id_to_group_name)
import logging

logger = logging.getLogger(__name__)


def get_eve_character_skills(character_id):
    logger.info("Gathering token for %s" % character_id)
    token = EveToken.objects.get(evecharacter__external_id=character_id)
    logger.info("Pulling skills of %s" % token.evecharacter.name)
    # resolve and clean skill list
    skills = EveClient.call(
        'get_characters_character_id_skills', token, character_id=character_id)['skills']
    for skill in skills:
        skill['skill_name'] = resolve_type_id_to_type_name(skill['skill_id'])
        skill['skill_type'] = resolve_type_id_to_group_name(skill['skill_id'])
    return skills
