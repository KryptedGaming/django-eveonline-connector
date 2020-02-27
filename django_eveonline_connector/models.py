from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from django.apps import apps 
import datetime, logging, json, traceback
logger = logging.getLogger(__name__)


"""
ESI Models
These models are used as wrappers around EsiPy
"""
from esipy import EsiClient, EsiSecurity, EsiApp
from django.core.cache import cache
class EveClient(models.Model):
    esi_base_url = models.URLField(
        default="https://esi.evetech.net/latest/swagger.json?datasource=tranquility")
    esi_callback_url = models.URLField()
    esi_client_id = models.CharField(max_length=255)
    esi_secret_key = models.CharField(max_length=255)

    def save(self, *args, **kwargs):
        self.pk = 0
        super(EveClient, self).save(*args, **kwargs)

    def __str__(self):
        return self.esi_callback_url

    @staticmethod
    def call(op, raise_exception=False, **kwargs):
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
            if 'token' in kwargs:
                token = kwargs.get('token') 
            elif 'character_id' in kwargs: 
                token = EveToken.objects.get(evecharacter__external_id=kwargs.get('character_id'), scopes__in=required_scopes) 
            elif 'corporation_id' in kwargs:
                eve_corporation = EveCorporation.objects.get(external_id=kwargs.get('corporation_id'))

                if not eve_corporation.ceo:
                    raise EveToken.DoesNotExist("Missing CEO Token with scopes %s for %s" % (required_scopes, eve_corporation.external_id))
            
                token_pk = eve_corporation.ceo.token.pk
                token = EveToken.objects.get(pk=token_pk, scopes__in=required_scopes)
            else:
                raise Exception("Attempted to make protected EsiCall without token or auto-matching keyword argument")
        else: 
            token = None 

        
        if token: 
            token.refresh()
            return EveClient.get_esi_client(token=token).request(operation(**kwargs), raise_on_error=raise_exception) 
        else: 
            return EveClient.get_esi_client().request(operation(**kwargs), raise_on_error=raise_exception) 

    @staticmethod
    def get_instance():
        app_config = apps.get_app_config('django_eveonline_connector')
        if app_config.ESI_SECRET_KEY and app_config.ESI_CLIENT_ID and app_config.ESI_CALLBACK_URL and app_config.ESI_BASE_URL:    
            return EveClient(
                    esi_client_id=app_config.ESI_CLIENT_ID,
                    esi_secret_key=app_config.ESI_SECRET_KEY,
                    esi_callback_url=app_config.ESI_CALLBACK_URL,
                    esi_base_url=app_config.ESI_BASE_URL)

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
            headers={'User-Agent': "Krypted Platform"})
        if token:
            esi_security.update_token(token.populate())
        return esi_security

    class Meta:
        verbose_name = "Eve Settings"
        verbose_name_plural = "Eve Settings"

"""
EVE SSO Models 
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

class EveTokenType(models.Model):
    name = models.CharField(max_length=32, unique=True)
    description = models.CharField(max_length=64)
    scopes = models.ManyToManyField("EveScope", blank=True)
    esi_sso_url = models.URLField(
        editable=False, max_length=2056)  # set on save

    def __str__(self):
        return self.name

    def get_scopes_list(self):
        return EveScope.convert_to_list(self.scopes.all())

    def get_scopes_string(self):
        return EveScope.convert_to_string(self.scopes.all())

class EveToken(models.Model):
    access_token = models.TextField()
    refresh_token = models.TextField()
    expires_in = models.IntegerField(default=0)
    expiry = models.DateTimeField(auto_now_add=True)
    scopes = models.ManyToManyField("EveScope", blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="eve_tokens", null=True)

    def __str__(self):
        try:
            return "<%s:%s>" % (self.evecharacter.name, self.user)
        except Exception as e:
            return "<%s:%s>" % ("Unknown Character", self.user)

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

    @staticmethod
    def create_from_external_id(external_id):
        response = EveClient.call('get_characters_character_id', character_id=external_id)

        eve_character = EveCharacter(
            name=response.data['name'],
            external_id=external_id)

        eve_character.save()

        return eve_character

class EveCorporation(EveEntity):
    ceo = models.OneToOneField(
        "EveCharacter", blank=True, null=True, on_delete=models.SET_NULL)
    ticker = models.CharField(max_length=5)
    alliance = models.ForeignKey(
        "EveAlliance", blank=True, null=True, on_delete=models.SET_NULL)

    @staticmethod
    def create_from_external_id(external_id):
        response = EveClient.call('get_corporations_corporation_id', corporation_id=external_id)
        eve_corporation = EveCorporation(
            name=response.data['name'],
            ticker=response.data['ticker'],
            external_id=external_id)

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
        response = EveClient.call('get_alliances_alliance_id', alliance_id=external_id)

        eve_alliance = EveAlliance(
            name=response.data['name'],
            ticker=response.data['ticker'],
            external_id=external_id)

        eve_alliance.save()

        return eve_alliance

"""
Entity Data Models 
These models represent entity data
"""
from django_eveonline_connector.utilities.esi.universe import *
from django_eveonline_connector.utilities.static.database_helpers import *
class EveAsset(models.Model):
    # ESI Data 
    is_blueprint_copy = models.BooleanField()
    is_singleton = models.BooleanField() 
    item_id = models.IntegerField()
    location_flag = models.CharField(max_length=64)
    location_id = models.IntegerField()
    location_type = models.CharField(max_length=64)
    quantity = models.IntegerField()
    type_id = models.IntegerField()

    # Mapped Static Data 
    group_id = models.IntegerField() 
    category_id = models.IntegerField()

    # Our Conversions
    item_name = models.CharField(max_length=128) # typeName
    item_type = models.CharField(max_length=32) # categoryName
    location = models.CharField(max_length=128)

    entity = models.ForeignKey(EveEntity, 
        on_delete=models.CASCADE, 
        related_name="assets")

    @staticmethod
    def get_bad_asset_categories():
        app_config = apps.get_app_config('django_eveonline_connector')
        return app_config.ESI_BAD_ASSET_CATEGORIES

    @staticmethod
    def create_from_esi_row(data_row, entity_external_id):
        try: 
            # Store what ESI returns 
            asset = EveAsset(
                is_singleton=data_row['is_singleton'],
                item_id=data_row['item_id'],
                location_flag=data_row['location_flag'],
                location_id=data_row['location_id'],
                location_type=data_row['location_type'],
                quantity=data_row['quantity'],
                type_id=data_row['type_id'])
            
            # Handle optional ESI fields 
            if 'is_blueprint_copy' in data_row:
                asset.is_blueprint_copy = True 
            else:
                asset.is_blueprint_copy = False 

            # Map useful static data
            asset.group_id = resolve_type_id_to_group_id(asset.type_id)
            asset.category_id = resolve_type_id_to_category_id(asset.type_id)

            # Use the static database to resolve EVE Model IDs
            asset.item_name = resolve_type_id_to_type_name(asset.type_id)
            asset.item_type = resolve_type_id_to_category_name(asset.type_id)

            # Location IDs suck to resolve, we must do different things for each type
            try:
                if asset.location_type == 'station':
                    asset.location = resolve_location_id_to_station(asset.location_id)
                elif asset.location_type == 'other':
                    asset.location = get_structure_id(asset.location_id)
                else:
                    asset.location = "Unknown Location"
            except Exception as e:
                asset.location = "Unknown Location"
                logger.error("Failed to resolve location for asset: %s" % str(e))

            asset.entity = EveEntity.objects.get(external_id=entity_external_id)
            asset.save() 

        except Exception as e:
            logging.exception("""Failed to create EveAsset from ESI data.
            ESI Data: %s, 
            """ % (data_row)
            )

"""
EVE Connector Models
Models for EVE Connector functionality 
"""
class PrimaryEveCharacterAssociation(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="primary_evecharacter")
    character = models.OneToOneField(EveCharacter, on_delete=models.CASCADE, related_name="primary_to")

    def __str__(self):
        return "<%s:%s>" % (self.user, self.character)

    def get_character(self):
        return self.character 

    def set_character(self, character):
        self.character = character 
        self.save() 

    def get_user(self):
        return self.user 

    def set_user(self):
        self.user = user 
        self.save() 