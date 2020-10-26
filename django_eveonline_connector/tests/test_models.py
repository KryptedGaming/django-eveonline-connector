from django.test import TestCase, Client, TransactionTestCase
from django.urls import reverse_lazy, reverse
from unittest.mock import patch
from django_eveonline_connector.models import *
from esipy import EsiClient
from pyswagger.io import Response as PySwaggerResponse
import pyswagger
import esipy
from django.apps import AppConfig
import django_eveonline_connector
from django.core.cache import cache
import uuid
from unittest import skip

# MOCK HELPERS 


class MockObject():
    pass


def mock_eve_client_call_character_public_data(*args, **kwargs):
    obj = MockObject()
    obj.data = {
        'name': 'BearThatCares'
    }
    return obj


def mock_eve_client_call_corporation_public_data(*args, **kwargs):
    obj = MockObject()
    obj.data = {
        'name': 'Doomheim',
        'ticker': 'HELL'
    }
    return obj

# ESI
class TestEveClient(TestCase):
    eve_client = None 
    eve_corporation_missing_ceo = None 
    eve_corporation_has_ceo = None
    eve_character = None 
    eve_ceo = None 
    eve_token = None 
    user = None 

    def setUp(self):
        self.eve_client = EveClient.objects.create(esi_callback_url="TEST", 
            esi_client_id="TEST", 
            esi_secret_key="TEST")

        self.user = User.objects.create_user(username="TEST", password="TEST")

        self.eve_token = EveToken.objects.create(
            access_token="123",
            refresh_token="123",
            user=self.user)

        self.eve_token.scopes.set(EveScope.objects.all())
        self.eve_ceo = EveCharacter.objects.create(
            name="TEST CHARACTER",
            external_id=1234,
            token=self.eve_token)

        self.eve_character = EveCharacter.objects.create(
            name="TEST CHARACTER",
            external_id=123)

        self.eve_corporation_missing_ceo = EveCorporation.objects.create(
            name="TEST",
            external_id=321,
            ticker="TEST")

        self.eve_corporation_has_ceo = EveCorporation.objects.create(
            name="TEST",
            external_id=421,
            ticker="TEST",
            ceo=self.eve_ceo)
    
    def tearDown(self):
        EveClient.objects.all().delete()

    def test_eve_client_save(self):
        self.eve_client.pk = 5 
        self.eve_client.save() 
        self.eve_client = EveClient.objects.all()[0]


    @patch('esipy.EsiClient.request')
    @patch('django_eveonline_connector.models.EveClient.get_esi_client')
    def test_eve_client_call_no_security(self, mock_get_esi_client, mock_esi_request):
        mock_get_esi_client.return_value=EsiClient(headers={'User-Agent': "Krypted Platform"})
        mock_esi_request.return_value=PySwaggerResponse(op='characters_character_id')
        response = self.eve_client.call('characters_character_id', character_id=634915984)
        self.assertIsInstance(response, PySwaggerResponse)

    def test_eve_client_call_required_scopes_character_id(self):
        from django_eveonline_connector.exceptions import EveMissingScopeException
        self.assertRaises(EveMissingScopeException, self.eve_client.call,
                          'characters_character_id_standings', character_id=634915984)
    
    def test_eve_client_call_required_scopes_corporation_id_does_not_exist(self):
        self.assertRaises(Exception, self.eve_client.call, 'characters_character_id_standings', corporation_id=98479678)

    def test_eve_client_call_required_scopes_corporation_id_without_ceo(self):
        from django_eveonline_connector.exceptions import EveMissingScopeException
        self.assertRaises(EveMissingScopeException, self.eve_client.call, 'characters_character_id_standings',
                          corporation_id=self.eve_corporation_missing_ceo.external_id)

    @patch('django_eveonline_connector.models.EveClient.get_esi_client')
    @patch('django_eveonline_connector.models.EveToken.refresh')
    @patch('esipy.EsiClient.request') 
    def test_eve_client_call_required_scopes_corporation_id_with_ceo(self, mock_esi_request, mock_token_refresh, mock_get_esi_client):
        op='corporations_corporation_id_members'
        mock_esi_request.return_value=PySwaggerResponse(op=op)
        mock_token_refresh.return_value=True
        mock_get_esi_client.return_value=EsiClient(headers={'User-Agent': "Krypted Platform"})
        response = self.eve_client.call(op, corporation_id=self.eve_corporation_has_ceo.external_id)
        self.assertIsInstance(response, PySwaggerResponse)

    def test_eve_client_get_instance(self):
        client = EveClient.get_instance() 
        self.assertTrue(client.esi_callback_url == self.eve_client.esi_callback_url)

    @patch('django.apps.apps.get_app_config')
    def test_eve_client_get_instance_app_config(self, mock_app_config):
        mock_app_config.return_value = AppConfig(app_name='django_eveonline_connector', 
            app_module=django_eveonline_connector)
        mock_app_config.return_value.ESI_CLIENT_ID="MOCKED"
        mock_app_config.return_value.ESI_SECRET_KEY="MOCKED"
        mock_app_config.return_value.ESI_CALLBACK_URL="MOCKED"
        mock_app_config.return_value.ESI_BASE_URL="MOCKED"
        client = EveClient.get_instance() 
        self.assertTrue("MOCKED" == client.esi_callback_url)

    def test_eve_client_get_instance_failed(self):
        self.eve_client.delete()
        self.assertRaises(Exception, EveClient.get_instance)
        self.eve_client = EveClient.objects.create(esi_callback_url="TEST", 
            esi_client_id="TEST", 
            esi_secret_key="TEST")

    def test_eve_client_get_esi_app(self):
        esi_app = self.eve_client.get_esi_app()
        self.assertIsInstance(esi_app, pyswagger.core.App)
        self.assertTrue('esi_app' in cache)
        esi_app = self.eve_client.get_esi_app()
        self.assertIsInstance(esi_app, pyswagger.core.App)

    @patch('django_eveonline_connector.models.EveClient.get_esi_security')
    def test_eve_client_get_esi_client(self, mock_get_esi_security):
        mock_get_esi_security.return_value = EsiSecurity(
            redirect_uri=self.eve_client.esi_callback_url,
            client_id=123,
            secret_key="123",
            headers={'User-Agent': "Krypted Platform"}
        )
        self.assertIsInstance(self.eve_client.get_esi_client(), esipy.EsiClient)
        self.assertIsInstance(self.eve_client.get_esi_client(self.eve_token), esipy.EsiClient)

    @patch('esipy.EsiSecurity.update_token')
    def test_eve_client_get_esi_security(self, mock_esi_security_update_token):
        self.assertIsInstance(self.eve_client.get_esi_security(), esipy.EsiSecurity)
        self.assertIsInstance(self.eve_client.get_esi_security(self.eve_token), esipy.EsiSecurity)

# SSO

class TestEveToken(TestCase):
    eve_token = None 
    user = None 

    def setUp(self):
        self.user = User.objects.create_user(
            username="TEST", 
            password="TEST")

        self.eve_token = EveToken.objects.create(
            access_token="TEST",
            refresh_token="TEST",
            user=self.user)

        self.eve_token.scopes.add(EveScope.objects.get_or_create(name="publicData")[0])

        self.eve_character = EveCharacter.objects.create(
            external_id=1,
            name="BearThatTests")
        
    def tearDown(self):
        self.user.delete() 
        self.eve_token.delete() 
        self.eve_character.delete() 

    def test_eve_token_str(self):
        self.assertTrue(self.eve_token.__str__() == "<Unknown Character:%s>" % self.user)
        self.eve_character.token = self.eve_token 
        self.eve_character.save() 
        self.assertTrue(self.eve_token.__str__() == "<%s:%s>" % (self.eve_character.name, self.user))

    @patch('esipy.EsiSecurity.refresh')
    @patch('django_eveonline_connector.models.EveClient.get_esi_security')
    def test_eve_token_refresh(self, mock_get_esi_security, mock_esi_security_refresh):
        mock_get_esi_security.return_value = EsiSecurity(
            redirect_uri="127.0.0.1",
            client_id=123,
            secret_key="123",
            headers={'User-Agent': "Krypted Platform"}
        )
        mock_esi_security_refresh.return_value = {
            'access_token': 'refreshed',
            'refresh_token': 'refreshed',
            'expires_in': 1500,
        }
        self.eve_token.refresh()

        with self.assertLogs('django_eveonline_connector', level='INFO') as cm:
            self.eve_token.refresh()
            self.assertTrue("Token refresh not needed" in cm.output[0])

class TestEveScope(TestCase):
    eve_scope_a = None 
    eve_scope_b = None 
    scopes = None 

    def setUp(self):
        self.eve_scope_a = EveScope.objects.create(name="test_scope_a")
        self.eve_scope_b = EveScope.objects.create(name="test_scope_b")
        self.scopes = EveScope.objects.filter(name__contains="test")

    def tearDown(self):
        self.eve_scope_a.delete() 
        self.eve_scope_b.delete()

    def test_eve_scope_str(self):
        self.assertTrue(self.eve_scope_a.__str__() == self.eve_scope_a.name)

    def test_eve_scope_convert_to_list(self):
        result = EveScope.convert_to_list(self.scopes).sort()
        expected_result = [self.eve_scope_a.name, self.eve_scope_b.name].sort()
        self.assertTrue(result == expected_result)

    def test_eve_scope_convert_to_string(self):
        result = EveScope.convert_to_string(self.scopes)
        expected_result = "%s,%s" % (self.eve_scope_a, self.eve_scope_b)

# ENTITIES
class TestEveEntity(TestCase):
    def test_eve_entity_str(self):
        ee = EveEntity.objects.create(name="TEST", external_id=0)
        self.assertTrue(ee.__str__() == ee.name)
        ee.delete()


class TestEveCharacter(TestCase):
    @patch.object(django_eveonline_connector.models.EveClient, 'call', mock_eve_client_call_character_public_data)
    def test_eve_character_create_from_external_id(self):
        ec = EveCharacter.create_from_external_id(634915984)
        self.assertTrue(ec.name == "BearThatCares")
        self.assertTrue(ec.external_id == 634915984)

class TestEveCorporation(TestCase):
    @patch.object(django_eveonline_connector.models.EveClient, 'call', mock_eve_client_call_corporation_public_data)
    def test_eve_corporation_create_from_external_id(self):
        ec = EveCorporation.create_from_external_id(1000001)
        self.assertTrue(ec.name == "Doomheim")
        self.assertTrue(ec.external_id == 1000001)

class TestEveAlliance(TestCase):
    # TODO: leaving as a sanity check that EveClient.call works.. find better way
    def test_eve_alliance_create_from_external_id(self):
        ea = EveAlliance.create_from_external_id(434243723)
        self.assertTrue(ea.name == "C C P Alliance")
        self.assertTrue(ea.external_id == 434243723)

# ENTITY DATA MODELS
class TestEveAsset(TestCase):
    esi_data_row = {
            "is_blueprint_copy": True,
            "is_singleton": False,
            "item_id": 18,
            "location_flag": "AssetSafety",
            "location_id": 60000004,
            "location_type": "station",
            "quantity": 5,
            "type_id": 1,
        }

    eve_entity = None
    
    def setUp(self):
        self.eve_entity = EveEntity.objects.create(name="TEST", external_id=1)
    
    def tearDown(self):
        self.eve_entity.delete()
        self.eve_entity = None 

    @skip("Fix later")
    @patch('django_eveonline_connector.models.resolve_location_from_location_id_location_type')
    @patch('django_eveonline_connector.models.resolve_type_id_to_category_name')
    @patch('django_eveonline_connector.models.resolve_type_id_to_type_name')
    @patch('django_eveonline_connector.models.resolve_type_id_to_category_id')
    @patch('django_eveonline_connector.models.resolve_type_id_to_group_id')
    def test_eve_asset_create_from_esi_row(self, mock_resolve_type_id_to_group_id, mock_resolve_type_id_to_category_id, mock_resolve_type_id_to_type_name, mock_resolve_type_id_to_category_name, mock_resolve_location_from_location_id_location_type):
        mock_resolve_type_id_to_group_id.return_value = 0
        mock_resolve_type_id_to_category_id.return_value = 0
        mock_resolve_type_id_to_type_name.return_value = "TestTypeName"
        mock_resolve_type_id_to_category_name.return_value = "TestCategoryName"
        mock_resolve_location_from_location_id_location_type.return_value = "Test Station - VII"
        EveAsset.create_from_esi_row(self.esi_data_row, self.eve_entity.external_id)

        eve_asset = EveAsset.objects.all()[0]
        self.assertTrue(eve_asset.is_blueprint_copy == self.esi_data_row['is_blueprint_copy'])
        self.assertTrue(eve_asset.is_singleton == self.esi_data_row['is_singleton'])
        self.assertTrue(eve_asset.item_id == self.esi_data_row['item_id'])
        self.assertTrue(eve_asset.location_flag == self.esi_data_row['location_flag'])
        self.assertTrue(eve_asset.location_id == self.esi_data_row['location_id'])
        self.assertTrue(eve_asset.location_type == self.esi_data_row['location_type'])
        self.assertTrue(eve_asset.type_id == self.esi_data_row['type_id'])
        self.assertTrue(eve_asset.group_id == mock_resolve_type_id_to_group_id.return_value)
        self.assertTrue(eve_asset.category_id == mock_resolve_type_id_to_category_id.return_value)
        self.assertTrue(eve_asset.item_name == mock_resolve_type_id_to_type_name.return_value)
        self.assertTrue(eve_asset.item_type == mock_resolve_type_id_to_category_name.return_value)
        self.assertTrue(eve_asset.location_name == mock_resolve_location_from_location_id_location_type.return_value)
        eve_asset.delete() 
        
        # remove blueprint copy
        self.esi_data_row.pop('is_blueprint_copy')
        EveAsset.create_from_esi_row(self.esi_data_row, self.eve_entity.external_id)
        eve_asset = EveAsset.objects.all()[0]
        self.assertTrue(eve_asset.is_blueprint_copy == False )
        eve_asset.delete() 

        # raise large exception 
        mock_resolve_type_id_to_group_id.side_effect = Exception()
        with self.assertLogs('django_eveonline_connector', level='WARNING') as cm:
            EveAsset.create_from_esi_row(self.esi_data_row, self.eve_entity.external_id)
            self.assertTrue("Failed to create" in cm.output[0])
        self.assertTrue(EveAsset.objects.all().count() == 0)

        
    def test_eve_asset_get_bad_asset_category_ids(self):
        self.assertTrue(EveAsset.get_bad_asset_category_ids() == [42, 43])
        
class TestEveJumpClone(TransactionTestCase):
    eve_data_row = {
        "implants": [1,2,3,4,5],
        "jump_clone_id": 56565496,
        "location_id": 1030491495855,
        "location_type": "structure",
        "name": ""
        }
    
    def setUp(self):
        EveEntity.objects.create(name="TEST_EJC", external_id=2)
    
    def tearDown(self):
        EveEntity.objects.all().delete()

    @patch('django_eveonline_connector.models.resolve_type_id_to_type_name')
    @patch('django_eveonline_connector.models.resolve_location_from_location_id_location_type')
    def test_create_from_esi_row(self, mock_resolve_location_from_location_id_location_type, mock_resolve_type_id_to_type_name):
        eve_entity = EveEntity.objects.get(name="TEST_EJC")
        mock_resolve_location_from_location_id_location_type.return_value = "My Location"
        mock_resolve_type_id_to_type_name.return_value = "Random Implant"
        EveJumpClone.create_from_esi_row(self.eve_data_row, eve_entity.external_id)

        expected_implant_string = "a,a,a,a,a".replace("a", mock_resolve_type_id_to_type_name.return_value)
        jump_clone = EveJumpClone.objects.all()[0]
        self.assertTrue(jump_clone.location_id == self.eve_data_row['location_id'])
        self.assertTrue(jump_clone.location_type == self.eve_data_row['location_type'])
        self.assertTrue(jump_clone.jump_clone_id == self.eve_data_row['jump_clone_id'])
        self.assertTrue(jump_clone.location == mock_resolve_location_from_location_id_location_type.return_value)
        self.assertTrue(jump_clone.implants == expected_implant_string)

# OTHER
class TestEveGroupRule(TestCase):
    def setUp(self):
        self.group = Group.objects.create(name="TEST")
        self.eve_group_rule = EveGroupRule.objects.create(group=self.group)
        self.user = User.objects.create(username="TEST USER")
        self.excluded_user = User.objects.create(username="EXCLUDED USER")
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

    def test_eve_group_rule_character_only(self):
        pre_valid_user_list = self.eve_group_rule.valid_user_list
        self.assertEqual(0, pre_valid_user_list.count())
        self.eve_group_rule.characters.add(self.eve_character)
        valid_user_list = self.eve_group_rule.valid_user_list
        self.assertEqual(1, valid_user_list.count())

    def test_eve_group_rule_corporation_only(self):
        self.eve_group_rule.corporations.add(self.eve_corporation)
        valid_user_list = self.eve_group_rule.valid_user_list
        self.assertEqual(1, valid_user_list.count())

    def test_eve_group_rule_alliance_only(self):
        self.eve_group_rule.alliances.add(self.eve_alliance)
        valid_user_list = self.eve_group_rule.valid_user_list
        self.assertEqual(1, valid_user_list.count())

    def test_eve_group_rule_compound(self):
        self.eve_group_rule.characters.add(self.eve_character)
        self.eve_group_rule.corporations.add(self.eve_corporation)
        self.eve_group_rule.alliances.add(self.eve_alliance)
        valid_user_list = self.eve_group_rule.valid_user_list
        self.assertEqual(1, valid_user_list.count())
        self.eve_character.corporation = None 
        self.eve_character.save() 
        valid_user_list = self.eve_group_rule.valid_user_list
        self.assertEqual(0, valid_user_list.count())

    def test_eve_group_rule_compound_with_role(self):
        self.eve_group_rule.characters.add(self.eve_character)
        self.eve_group_rule.roles.add(EveCorporationRole.objects.get(name="Hangar Take 1"))
        self.assertEqual(0, self.eve_group_rule.valid_user_list.count())
        self.eve_character.roles.add(
            EveCorporationRole.objects.get(name="Hangar Take 1"))
        self.assertEqual(1, self.eve_group_rule.valid_user_list.count())

    def test_invalid_user_list(self):
        self.excluded_user.groups.add(self.group)
        self.user.groups.add(self.group)
        self.eve_group_rule.characters.add(self.eve_character)
        self.assertEqual(1, self.eve_group_rule.invalid_user_list.count())