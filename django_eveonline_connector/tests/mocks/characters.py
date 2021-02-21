from .generic import MockResponseObject
from django_eveonline_connector.tests.utilities import random_external_id


def get_mock_affiliations_test_data(character_id1, character_id2, corporation_id):
    return MockResponseObject(
        status=200,
        data=[
            {
                "character_id": character_id1,
                "corporation_id": corporation_id,
            },
            {
                "character_id": character_id2,
                "corporation_id": random_external_id()
            }
        ]
    )
