from django.db import models
from django.utils import timezone
from django.core.cache import cache
from django.contrib.auth.models import User
from esipy import EsiClient, EsiSecurity, EsiApp
import datetime
import logging
import json
logger = logging.getLogger(__name__)

"""
OAuth Models
These models are used for the EVE Online token system
"""


class EveScope(models.Model):
    name = models.TextField()

    def __str__(self):
        return self.name

    @staticmethod
    def get_formatted_scopes():
        return [scope.name for scope in EveScope.objects.all()]


class EveClient(models.Model):
    esi_base_url = models.URLField(
        default="https://esi.evetech.net/latest/swagger.json?datasource=tranquility")
    esi_callback_url = models.URLField()
    esi_sso_url = models.URLField(editable=False, max_length=2056)  # set on save
    esi_client_id = models.CharField(max_length=255)
    esi_secret_key = models.CharField(max_length=255)

    def save(self, *args, **kwargs):
        if EveClient.objects.all():
            EveClient.objects.all()[0].delete()

        self.esi_sso_url = EsiSecurity(
            client_id=self.esi_client_id,
            redirect_uri=self.esi_callback_url,
            secret_key=self.esi_secret_key,
            headers={'User-Agent': "Krypted Platform"}
        ).get_auth_uri(scopes=EveScope.get_formatted_scopes(),
                       state=self.esi_client_id)

        super(EveClient, self).save(*args, **kwargs)

    def __str__(self):
        return self.esi_callback_url

    @staticmethod
    def call(operation, token=None, **kwargs):
        if token:
            token.refresh()
        esi_client = EveClient.get_esi_client(token=token)
        return esi_client.request(EveClient.get_esi_app().op[operation](**kwargs)).data

    @staticmethod
    def call_raw(operation, token=None, **kwargs):
        if token:
            token.refresh()
        esi_client = EveClient.get_esi_client(token=token)
        return esi_client.request(EveClient.get_esi_app().op[operation](**kwargs))

    @staticmethod
    def get_instance():
        if not EveClient.objects.all():
            raise Exception(
                "EveClient must be created in administration panel before using EVE Online connector.")
        else:
            if 'X-Esi-Error-Limited' in cache and cache.get('X-Esi-Error-Limited') <= 1:
                logger.error(
                    "EveClient has hit ESI Error limit, not allowing any EveClient instances")
                return None
            return EveClient.objects.all()[0]

    @staticmethod
    def get_esi_app():
        """
        EsiApp is used to get operations for Eve Swagger Interface 
        """
        if 'esi_app' in cache:
            return cache.get('esi_app')
        else:
            esi_app = EsiApp(cache_time=86400).get_latest_swagger
            cache.set('esi_app', esi_app, timeout=86400)
            return esi_app

    @staticmethod
    def get_esi_client(token=None):
        """
        EsiClient is used to call operations for Eve Swagger Interface 
        """
        return EsiClient(security=EveClient.get_esi_security(token), headers={'User-Agent': "Krypted Platform"})

    @staticmethod
    def get_esi_security(token=None):
        """
        EsiSecurity is used to refresh and manage EVE Token objects
        """
        client = EveClient.get_instance()
        esi_security = EsiSecurity(
            redirect_uri=client.esi_callback_url,
            client_id=client.esi_client_id,
            secret_key=client.esi_secret_key,
            headers={'User-Agent': "Krypted Platform"}
        )
        if token:
            esi_security.update_token(token.populate())
        return esi_security


class EveToken(models.Model):
    access_token = models.TextField()
    refresh_token = models.TextField()
    expires_in = models.IntegerField(default=0)
    expiry = models.DateTimeField(auto_now_add=True)
    scopes = models.ManyToManyField("EveScope", blank=True)
    user = models.ForeignKey(
        User, null=True, on_delete=models.CASCADE, related_name="eve_tokens")
    primary = models.BooleanField(default=False)

    def __str__(self):
        try:
            return "<%s:%s>" % (self.evecharacter.name, self.user)
        except Exception as e:
            return "<%s:%s>" % ("Unknown Character", self.user)

    def save(self, *args, **kwargs):
        if self.primary and EveToken.objects.filter(user=self.user, primary=True).exists():
            if self.pk and EveToken.objects.filter(pk=self.pk, user=self.user, primary=True).exists():
                super(EveToken, self).save(*args, **kwargs)
            else:
                raise Exception(
                    "Attempted to save a primary character, but primary character already exists.")
        super(EveToken, self).save(*args, **kwargs)

    def get_primary_token(self):
        return EveToken.objects.filter(user=self.user, primary=True).first()
    
    def get_primary_character(self):
        if self.primary == True: 
            return self.evecharacter
        else:
            return self.get_primary_token().evecharacter

    @staticmethod
    def format_scopes(scopes):
        if type(scopes) is str:
            return scopes.split(",")
        else:
            return ",".join(scopes)

    def refresh(self):
        esi_security = EveClient.get_esi_security()
        esi_security.update_token(self.populate())
        new_token = esi_security.refresh()
        if timezone.now() > self.expiry:
            self.access_token = new_token['access_token']
            self.refresh_token = new_token['refresh_token']
            self.expiry = timezone.now() + datetime.timedelta(0,
                                                              new_token['expires_in'])
            self.save()
        else:
            logger.info("Token refresh not needed")

    def populate(self):
        data = {}
        data['access_token'] = self.access_token
        data['refresh_token'] = self.refresh_token
        data['expires_in'] = self.expires_in

        return data


"""
Entity Models
These entity models are what all EVE Online data models are attached to.
"""


class EveEntity(models.Model):
    name = models.CharField(max_length=128)
    external_id = models.IntegerField(unique=True)

    def __str__(self):
        return self.name


class EveCharacter(EveEntity):
    corporation = models.ForeignKey(
        "EveCorporation", on_delete=models.SET_NULL, null=True)

    token = models.OneToOneField(
        "EveToken", on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return self.name

    @staticmethod
    def create_from_external_id(external_id):
        esi_operation = EveClient.get_esi_app(
        ).op['get_characters_character_id'](character_id=external_id)
        response = EveClient.get_esi_client().request(esi_operation)

        eve_character = EveCharacter(
            name=response.data['name'],
            external_id=external_id
        )

        eve_character.save()

        return eve_character


class EveCorporation(EveEntity):
    ceo = models.OneToOneField(
        "EveCharacter", blank=True, null=True, on_delete=models.SET_NULL)
    ticker = models.CharField(max_length=5)
    alliance = models.ForeignKey(
        "EveAlliance", blank=True, null=True, on_delete=models.SET_NULL)

    def save(self, *args, **kwargs):
        super(EveCorporation, self).save(*args, **kwargs)

    @staticmethod
    def create_from_external_id(external_id):
        esi_operation = EveClient.get_esi_app(
        ).op['get_corporations_corporation_id'](corporation_id=external_id)
        response = EveClient.get_esi_client().request(esi_operation)

        eve_corporation = EveCorporation(
            name=response.data['name'],
            ticker=response.data['ticker'],
            external_id=external_id
        )

        eve_corporation.save()

        return eve_corporation


class EveAlliance(EveEntity):
    executor = models.OneToOneField(
        "EveCorporation", blank=True, null=True, on_delete=models.SET_NULL)
    ticker = models.CharField(max_length=5)

    def save(self, *args, **kwargs):
        super(EveAlliance, self).save(*args, **kwargs)

    @staticmethod
    def create_from_external_id(external_id):
        esi_operation = EveClient.get_esi_app(
        ).op['get_alliances_alliance_id'](alliance_id=external_id)
        response = EveClient.get_esi_client().request(esi_operation)

        eve_alliance = EveAlliance(
            name=response.data['name'],
            ticker=response.data['ticker'],
            external_id=external_id
        )

        eve_alliance.save()

        return eve_alliance
