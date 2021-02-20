import uuid
import datetime
from django_eveonline_connector.models import EveToken, EveScope, EveCharacter, EveCorporation, EveAlliance
from unittest.mock import patch


def clean_eve_models():
    EveToken.objects.all().delete()
    EveCharacter.objects.all().delete()
    EveCorporation.objects.all().delete()
    EveAlliance.objects.all().delete()


@patch('django_eveonline_connector.models.EveCorporation.validate_ceo')
def create_tracked_eve_character(mock_validate_ceo):
    mock_validate_ceo.return_value = True
    token = EveToken.objects.create(
        access_token=uuid.uuid4(),
        refresh_token=uuid.uuid4(),
        expiry=datetime.datetime.utcnow() + datetime.timedelta(days=1)
    )
    token.scopes.set(EveScope.objects.filter(required=True))

    character = EveCharacter.objects.create(
        external_id=uuid.uuid4().int & (1 << 32)-1,
        name=f"test_{uuid.uuid4()}",
        token=token
    )

    corporation = EveCorporation.objects.create(
        external_id=uuid.uuid4().int & (1 << 32)-1,
        name=f"test_{uuid.uuid4()}",
        ceo=character,
        ticker=f"TEST",
        track_corporation=True,
        track_characters=True
    )

    character.corporation = corporation
    character.save()

    return character


@patch('django_eveonline_connector.models.EveCorporation.validate_ceo')
def create_tracked_eve_corporation(mock_validate_ceo):
    mock_validate_ceo.return_value = True
    token = EveToken.objects.create(
        access_token=uuid.uuid4(),
        refresh_token=uuid.uuid4(),
        expiry=datetime.datetime.utcnow() + datetime.timedelta(days=1)
    )
    token.scopes.set(EveScope.objects.filter(required=True))

    character = EveCharacter.objects.create(
        external_id=uuid.uuid4().int & (1 << 32)-1,
        name=f"test_{uuid.uuid4()}",
        token=token
    )

    corporation = EveCorporation.objects.create(
        external_id=uuid.uuid4().int & (1 << 32)-1,
        name=f"test_{uuid.uuid4()}",
        ceo=character,
        ticker=f"TEST",
        track_corporation=True,
        track_characters=True
    )

    character.corporation = corporation
    character.save()

    return corporation
