from django_eveonline_connector.models import EveCorporation


def mock_corporation_update_related_characters():
    corporation = EveCorporation.objects.get_or_create(
        external_id=200, name="DUMMY CORPORATION")[0]
    character_2 = EveCharacter.objects.get(external_id=2)
    character_4 = EveCharacter.objects.get(external_id=4)
    character_2.corporation = corporation
    character_4.corporation = corporation
    character_2.save()
    character_4.save()


def mock_corporation_create_from_external_id(corporation_id):
    return EveCorporation.objects.create(
        external_id=corporation_id,
        name="Test Corporation"
    )
