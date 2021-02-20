from django.test import TestCase
from django.contrib.auth.models import User, Group
from django.utils import timezone
from django_eveonline_connector.tasks import update_tokens
from django_eveonline_connector.models import(EveToken, EveCharacter, EveCorporation,
                                              EveAlliance, EveClient, EveScope,
                                              EveGroupRule)
from django_eveonline_connector.tests.mocks.corporations import mock_corporation_create_from_external_id
from django_eveonline_connector.tests.mocks.generic import MockResponseObject
from django_eveonline_connector.tests.utilities import clean_eve_models, create_tracked_eve_character, create_tracked_eve_corporation
from unittest.mock import patch
from datetime import timedelta
import pytz


class TestEveTokenTasks(TestCase):
    def setUp(self):
        self.client = EveClient.objects.create(esi_callback_url="TEST",
                                               esi_client_id="TEST",
                                               esi_secret_key="TEST")

    def tearDown(self):
        self.client.delete()

    @patch('django_eveonline_connector.models.EveToken.refresh')
    def test_update_tokens_skip_valid_tokens(self, mock_refresh):
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
    def test_update_tokens_invalidate_bad_tokens(self, mock_refresh):
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
    def test_update_tokens_delete_invalidated_tokens(self, mock_refresh):
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


class EveGroupTest(TestCase):
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


class TestEveCharacterTasks(TestCase):
    def setUp(self):
        self.valid_characters = [
            create_tracked_eve_character(),
            create_tracked_eve_character()
        ]
        self.invalid_characters = [
            EveCharacter.objects.create(external_id=3, name="Invalid A"),
            EveCharacter.objects.create(external_id=4, name="Invalid B"),
            EveCharacter.objects.create(external_id=5, name="Invalid B")
        ]

    def tearDown(self):
        clean_eve_models()

    @patch('django_eveonline_connector.tasks.update_character')
    def test_update_characters(self, mock_update_character):
        from django_eveonline_connector.tasks import update_characters
        mock_update_character.return_value = None
        update_characters()
        self.assertTrue(True)

    @patch('django_eveonline_connector.models.EveCharacter.update_character_corporation_roles')
    @patch('django_eveonline_connector.models.EveCharacter.update_character_corporation')
    @patch('django_eveonline_connector.tasks.update_character_transactions')
    @patch('django_eveonline_connector.tasks.update_character_skills')
    @patch('django_eveonline_connector.tasks.update_character_jumpclones')
    @patch('django_eveonline_connector.tasks.update_character_journal')
    @patch('django_eveonline_connector.tasks.update_character_contracts')
    @patch('django_eveonline_connector.tasks.update_character_contacts')
    @patch('django_eveonline_connector.tasks.update_character_assets')
    def test_update_character(self,
                              mock_update_character_assets,
                              mock_update_character_contacts,
                              mock_update_character_contracts,
                              mock_update_character_journal,
                              mock_update_character_jumpclones,
                              mock_update_character_skills,
                              mock_update_character_transactions,
                              mock_update_character_corporation,
                              mock_update_character_corporation_roles
                              ):
        from django_eveonline_connector.tasks import update_character
        mock_update_character_assets.return_value = None
        mock_update_character_contacts.return_value = None
        mock_update_character_contracts.return_value = None
        mock_update_character_journal.return_value = None
        mock_update_character_skills.return_value = None
        mock_update_character_transactions.return_value = None
        mock_update_character_corporation.return_value = None
        mock_update_character_corporation_roles.return_value = None
        update_character(3)


class TestEveCorporationTasks(TestCase):
    def tearDown(self):
        clean_eve_models()

    @patch('django_eveonline_connector.tasks.update_corporation')
    def test_update_corporations(self, mock_update_corporation):
        from django_eveonline_connector.tasks import update_corporations
        mock_update_corporation.return_value = None
        tracked_corporation = create_tracked_eve_corporation()

        untracked_corporation = create_tracked_eve_corporation()
        untracked_corporation.track_corporation = False
        untracked_corporation.save()

        invalid_corporation = EveCorporation.objects.create(
            external_id=1, name="INVALID")

        update_corporations()
        self.assertEqual(EveCorporation.objects.all().count(), 2)

    @patch('django_eveonline_connector.models.EveCorporation.validate_ceo')
    @patch('django_eveonline_connector.models.EveCorporation.update_related_characters')
    @patch('django_eveonline_connector.models.EveCorporation.update_ceo')
    @patch('django_eveonline_connector.models.EveCorporation.update_alliance')
    def test_update_corporation_valid_corporation(self, mock_update_alliance, mock_update_ceo, mock_update_related_characters, mock_validate_ceo):
        from django_eveonline_connector.tasks import update_corporation
        mock_update_alliance.return_value = None
        mock_update_ceo.return_value = None
        mock_update_related_characters.return_value = None
        mock_validate_ceo.return_value = True
        tracked_corporation = create_tracked_eve_corporation()
        update_corporation(tracked_corporation.external_id)

    @patch('django_eveonline_connector.models.EveCorporation.update_related_characters')
    @patch('django_eveonline_connector.models.EveCorporation.update_ceo')
    @patch('django_eveonline_connector.models.EveCorporation.update_alliance')
    def test_update_corporation_invalid_corporation(self, mock_update_alliance, mock_update_ceo, mock_update_related_characters):
        from django_eveonline_connector.tasks import update_corporation
        mock_update_alliance.return_value = None
        mock_update_ceo.return_value = None
        mock_update_related_characters.return_value = None
        untracked_corporation = create_tracked_eve_corporation()
        untracked_corporation.track_corporation = False
        untracked_corporation.save()

        update_corporation(untracked_corporation.external_id)

    @patch('django_eveonline_connector.models.EveCorporation.validate_ceo')
    @patch('django_eveonline_connector.models.EveCorporation.update_related_characters')
    @patch('django_eveonline_connector.models.EveCorporation.update_ceo')
    @patch('django_eveonline_connector.models.EveCorporation.update_alliance')
    def test_update_corporation_invalidate_corporation(self, mock_update_alliance, mock_update_ceo, mock_update_related_characters, mock_validate_ceo):
        from django_eveonline_connector.tasks import update_corporation
        mock_update_alliance.return_value = None
        mock_update_ceo.return_value = None
        mock_update_related_characters.return_value = None
        mock_validate_ceo.return_value = False
        tracked_corporation = create_tracked_eve_corporation()
        with self.assertLogs('django_eveonline_connector', level='INFO') as cm:
            update_corporation(tracked_corporation.external_id)
        tracked_corporation.refresh_from_db()
        self.assertFalse(tracked_corporation.track_corporation)

    @patch('django_eveonline_connector.tasks.update_corporation_eveentitydata')
    def test_update_structures(self, mock_update_corporation_eveentitydata):
        from django_eveonline_connector.tasks import update_structures
        mock_update_corporation_eveentitydata.return_value = False
        tracked_corporation = create_tracked_eve_corporation()

        untracked_corporation = create_tracked_eve_corporation()
        untracked_corporation.track_corporation = False
        untracked_corporation.save()
        update_structures()


class TestEveAllianceTasks(TestCase):
    def setUp(self):
        self.alliance = EveAlliance.objects.create(
            external_id=1, name="Test Alliance")

    def tearDown(self):
        EveAlliance.objects.all().delete()
        EveCorporation.objects.all().delete()
        EveCharacter.objects.all().delete()

    @patch('django_eveonline_connector.tasks.update_alliance')
    def test_update_alliances(self, mock_update_alliance):
        from django_eveonline_connector.tasks import update_alliances
        mock_update_alliance.return_value = None
        update_alliances()

    @patch('django_eveonline_connector.models.EveClient.call')
    @patch('django_eveonline_connector.models.EveCorporation.create_from_external_id')
    def test_update_alliance_unknown_corporation(self, mock_corporation_call, mock_eve_client_call):
        from django_eveonline_connector.tasks import update_alliance
        corporation_id = 2
        mock_corporation_call.side_effect = mock_corporation_create_from_external_id
        mock_eve_client_call.return_value = MockResponseObject(
            status=200,
            data={"executor_corporation_id": corporation_id}
        )
        update_alliance(self.alliance.external_id)
        self.assertTrue(EveAlliance.objects.get(
            external_id=self.alliance.external_id).executor.external_id, corporation_id)

    @patch('django_eveonline_connector.models.EveClient.call')
    @patch('django_eveonline_connector.models.EveCorporation.create_from_external_id')
    def test_update_alliance_known_corporation(self, mock_corporation_call, mock_eve_client_call):
        from django_eveonline_connector.tasks import update_alliance
        corporation_id = 3
        EveCorporation.objects.create(
            external_id=corporation_id,
            name="Test Corporation"
        )
        mock_corporation_call.side_effect = mock_corporation_create_from_external_id
        mock_eve_client_call.return_value = MockResponseObject(
            status=200,
            data={"executor_corporation_id": corporation_id}
        )

        update_alliance(self.alliance.external_id)
        self.assertTrue(EveAlliance.objects.get(
            external_id=self.alliance.external_id).executor.external_id, corporation_id)

    @patch('django_eveonline_connector.models.EveClient.call')
    @patch('django_eveonline_connector.models.EveCorporation.create_from_external_id')
    def test_update_alliance_closed_alliance(self, mock_corporation_call, mock_eve_client_call):
        from django_eveonline_connector.tasks import update_alliance
        corporation_id = 4
        EveCorporation.objects.create(
            external_id=corporation_id,
            name="Test Corporation"
        )
        mock_corporation_call.side_effect = mock_corporation_create_from_external_id
        mock_eve_client_call.return_value = MockResponseObject(
            status=200,
            data={"creator_corporation_id": corporation_id}
        )
        update_alliance(self.alliance.external_id)
        self.assertTrue(EveAlliance.objects.get(
            external_id=self.alliance.external_id).executor.external_id, corporation_id)
