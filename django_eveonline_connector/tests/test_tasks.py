from django_eveonline_connector.tasks import update_tokens, pull_corporation_roster
from django_eveonline_connector.models import *
from django.contrib.auth.models import User, Group
from django.test import TestCase
from datetime import timedelta
from django.utils import timezone
import pytz
from unittest.mock import patch

class MockResponseObject():
    def __init__(self, status_code, data):
        self.status_code = status_code 
        self.data = data

def mock_update_corporations_for_pull_test():
    corporation = EveCorporation.objects.get_or_create(external_id=200, name="DUMMY CORPORATION")[0]
    character_2 = EveCharacter.objects.get(external_id=2)
    character_4 = EveCharacter.objects.get(external_id=4)
    character_2.corporation = corporation
    character_4.corporation = corporation
    character_2.save()
    character_4.save()
class UpdateTokenTest(TestCase):
    def setUp(self):
        self.client = EveClient.objects.create(esi_callback_url="TEST",
                                 esi_client_id="TEST",
                                 esi_secret_key="TEST")

    def tearDown(self):
        self.client.delete() 

    @patch('django_eveonline_connector.models.EveToken.refresh')
    def test_valid_token(self, mock_refresh):
        mock_refresh.return_value = True
        character = EveCharacter.objects.create(
            external_id=12345,
            name="Test Character"
        )
        token = EveToken.objects.create()
        character.token = token 
        character.save() 
        token.scopes.set(EveScope.objects.all())
        self.assertTrue(token.valid)
        update_tokens()
        self.assertTrue(EveToken.objects.all().count() == 1)
        self.assertTrue(EveToken.objects.all()[0].pk == token.pk)
        self.assertTrue(EveToken.objects.all()[0].invalidated == None)
        token.delete()

    @patch('django_eveonline_connector.models.EveToken.refresh')
    def test_invalidating_token(self, mock_refresh):
        mock_refresh.return_value = True
        character = EveCharacter.objects.create(
            external_id=12345,
            name="Test Character"
        )
        token = EveToken.objects.create()
        character.token = token 
        character.save()
        token.scopes.set(EveScope.objects.all())
        token.scopes.remove(EveScope.objects.filter(required=True)[0])
        self.assertFalse(token.valid)
        update_tokens()
        self.assertTrue(EveToken.objects.all().count() == 1)
        token = EveToken.objects.all()[0]
        self.assertTrue((timezone.now() - token.invalidated).days == 0)
        self.assertTrue(token.pk == token.pk)
        self.assertTrue(token.invalidated != None)

    @patch('django_eveonline_connector.models.EveToken.refresh')
    def test_delete_invalidated_token(self, mock_refresh):
        mock_refresh.return_value = True
        token = EveToken.objects.create()
        character = EveCharacter.objects.create(
            external_id=12345,
            name="Test Character"
        )
        character.token = token 
        character.save()
        token.scopes.set(EveScope.objects.all())
        token.scopes.remove(EveScope.objects.filter(required=True)[0])
        self.assertFalse(token.valid)
        update_tokens()
        token.invalidated = timezone.now() - timedelta(days=6)
        token.save()
        update_tokens()
        self.assertTrue(EveToken.objects.all().count() == 1)
        token.invalidated = timezone.now() - timedelta(days=8)
        token.save()
        update_tokens()
        self.assertTrue(EveToken.objects.all().count() == 0)

class PullCorporationRoster(TestCase):
    def setUp(self):
        self.corporation = EveCorporation.objects.create(external_id=100, name="TEST CORPORATION")
        EveCharacter.objects.create(
            external_id=1, corporation=self.corporation)
        EveCharacter.objects.create(
            external_id=2, corporation=self.corporation)
        EveCharacter.objects.create(
            external_id=3, corporation=self.corporation)
        EveCharacter.objects.create(
            external_id=4, corporation=self.corporation)
        EveCharacter.objects.create(
            external_id=5, corporation=self.corporation)

    @patch('django_eveonline_connector.tasks.EveClient.call')
    @patch('django_eveonline_connector.models.EveCharacter.update_character_corporation')
    def test_pull_roster(self, mock_character_update, mock_eve_client):
        mock_character_update.return_value = MockResponseObject(status_code=200, data=[200])
        mock_character_update.side_effect = mock_update_corporations_for_pull_test()
        mock_eve_client.return_value = MockResponseObject(status_code=200, data=[1,3,5])
        pull_corporation_roster(self.corporation.external_id)
        characters = EveCharacter.objects.filter(corporation=self.corporation)
        character_ids = characters.values_list('external_id', flat=True)
        self.assertTrue(list(character_ids) == [1,3,5])


class AssignEveGroupsTest(TestCase):
    def setUp(self):
        self.group = Group.objects.create(name="TEST")
        self.eve_group_rule = EveGroupRule.objects.create(group=self.group)
        self.user = User.objects.create(username="TEST USER")
        self.excluded_user = User.objects.create(username="EXCLUDED USER")
        self.excluded_user_2 = User.objects.create(username="EXCLUDED USER 2")
        self.eve_token = EveToken.objects.create(user=self.user)
        self.eve_alliance = EveAlliance.objects.create(
            name="TEST ALLIANCE PLEASE IGNORE",
            external_id=912345
        )
        self.eve_corporation = EveCorporation.objects.create(
            name="TEST CORPORATION",
            alliance=self.eve_alliance,
            external_id=512345
        )
        self.eve_character = EveCharacter.objects.create(name="TEST",
            token=self.eve_token,
            corporation=self.eve_corporation,
            external_id=112345)

    def tearDown(self):
        self.group.delete()
        self.eve_group_rule.delete()
        self.eve_token.delete()
        self.eve_alliance.delete()
        self.eve_corporation.delete()
        self.eve_character.delete()

    def test_group_assignment(self):
        from django_eveonline_connector.tasks import assign_eve_groups
        self.excluded_user.groups.add(self.group)
        self.excluded_user_2.groups.add(self.group)
        self.eve_group_rule.characters.add(self.eve_character)
        assign_eve_groups()
        self.assertTrue(self.group not in self.excluded_user.groups.all())
        self.assertTrue(self.group not in self.excluded_user_2.groups.all())
        self.assertTrue(self.group in self.user.groups.all())
