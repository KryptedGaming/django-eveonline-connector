from django_eveonline_connector.tasks import update_tokens
from django_eveonline_connector.models import EveToken, EveScope, EveClient
from django.test import TestCase
from datetime import timedelta
from django.utils import timezone
import pytz
from unittest.mock import patch

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
        token = EveToken.objects.create()
        token.scopes.set(EveScope.objects.all())
        self.assertTrue(token.valid)
        update_tokens()
        self.assertTrue(EveToken.objects.all().count() == 1)
        self.assertTrue(EveToken.objects.all()[0].pk == token.pk)
        self.assertTrue(EveToken.objects.all()[0].invalidated == None)

    @patch('django_eveonline_connector.models.EveToken.refresh')
    def test_invalidating_token(self, mock_refresh):
        mock_refresh.return_value = True
        token = EveToken.objects.create()
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
