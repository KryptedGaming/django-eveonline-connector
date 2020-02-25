from django.test import TestCase, Client
from django.urls import reverse_lazy, reverse
from django_eveonline_connector.models import EveScope
import uuid

class TestEveOnlineModels(TestCase):
    def setUp(self):
        pass
        
    def test_eve_scope(self):
        eve_scope = EveScope.objects.create(name="django_eveonline_test_scope")

        self.assertTrue(eve_scope.__str__() == eve_scope.name)
        self.assertTrue(EveScope.get_formatted_scopes() == ["django_eveonline_test_scope"])

        eve_scope.delete()

    def test_eve_client(self):
        eve_scope = EveScope.objects.create(name="django_eveonline_test_scope")