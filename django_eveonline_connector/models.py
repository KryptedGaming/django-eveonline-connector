from django.db import models
from django.utils import timezone
from django.core.cache import cache
from django.apps import apps 
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
    def convert_to_list(scopes):
        return [scope.name for scope in scopes]

    @staticmethod
    def convert_to_string(scopes):
        return ",".join([scope.name for scope in scopes])

class EveClient(models.Model):
    esi_base_url = models.URLField(
        default="https://esi.evetech.net/latest/swagger.json?datasource=tranquility")
    esi_callback_url = models.URLField()
    esi_client_id = models.CharField(max_length=255)
    esi_secret_key = models.CharField(max_length=255)

    def save(self, *args, **kwargs):
        if EveClient.objects.all():
            EveClient.objects.all()[0].delete()

        super(EveClient, self).save(*args, **kwargs)

    def __str__(self):
        return self.esi_callback_url

    @staticmethod
    def call(op, **kwargs):
        operation = EveClient.get_esi_app().op[op]
        # Pull the required scopes from the ESI Swagger Definition
        required_scopes = set() 
        if operation.security:
            for definition in operation.security:
                if 'evesso' in definition: 
                    for scope_name in definition['evesso']:
                        scope_creation = EveScope.objects.get_or_create(name=scope_name)
                        scope = scope_creation[0]
                        if scope_creation[1]:
                            logger.error("Encountered unknown scope '%s', please notify Krypted developers." % scope)
                        required_scopes.add(scope)
        
        # Find the token with proper scopes and access 
        if required_scopes:
            if 'character_id' in kwargs: 
                token = EveToken.objects.get(evecharacter__external_id=kwargs.get('character_id'), scopes__in=required_scopes) 

            if 'corporation_id' in kwargs:
                # we require a CEO token for corporaition actions
                try: 
                    eve_corporation = EveCorporation.objects.get(external_id=kwargs.get('corporation_id'))
                except EveCorporation.DoesNotExist:
                    raise Exception("Attempted to pull protected ESI data from EveCorporation that does not exist")
                
                if not eve_corporation.ceo:
                    raise Exception("Attempted to pull information for EveCorporation with non-existent CEO EveToken")

                token_pk = eve_corporation.ceo.token.pk
                EveToken.objects.get(pk=token_pk, scopes__in=required_scopes)
        else: 
            token = None 

        
        if token: 
            token.refresh()
            return EveClient.get_esi_client(token=token).request(operation(**kwargs)) 
        else: 
            return EveClient.get_esi_client().request(operation(**kwargs)) 

    @staticmethod
    def call_raw(operation, token=None, **kwargs):
        if token:
            token.refresh()
        esi_client = EveClient.get_esi_client(token=token)
        return esi_client.request(EveClient.get_esi_app().op[operation](**kwargs))

    @staticmethod
    def get_instance():
        app_config = apps.get_app_config('django_eveonline_connector')
        if app_config.ESI_SECRET_KEY and app_config.ESI_CLIENT_ID and app_config.ESI_CALLBACK_URL and app_config.ESI_BASE_URL:    
            return EveClient(
                    esi_client_id=app_config.ESI_CLIENT_ID,
                    esi_secret_key=app_config.ESI_SECRET_KEY,
                    esi_callback_url=app_config.ESI_CALLBACK_URL,
                    esi_base_url=app_config.ESI_BASE_URL,
                )
        elif EveClient.objects.all():
            return EveClient.objects.all()[0]
        raise Exception("EveClient is not configured.")

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
        if token:
            return EsiClient(security=EveClient.get_esi_security(token), headers={'User-Agent': "Krypted Platform"})
        else:
            return EsiClient(headers={'User-Agent': "Krypted Platform"})

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

    class Meta:
        verbose_name = "Eve Settings"
        verbose_name_plural = "Eve Settings"

class EveTokenType(models.Model):
    name = models.CharField(max_length=32, unique=True)
    description = models.CharField(max_length=64)
    scopes = models.ManyToManyField("EveScope", blank=True)
    esi_sso_url = models.URLField(
        editable=False, max_length=2056)  # set on save

    def __str__(self):
        return self.name

    def get_scopes_list(self):
        if self.scopes.all():
            return EveScope.convert_to_list(self.scopes.all())
        return []

    def get_scopes_string(self):
        if self.scopes.all():
            return EveScope.convert_to_string(self.scopes.all())
        return []

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
            token = self.get_primary_token()
            if token:
                return token.evecharacter
            else:
                return None

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
