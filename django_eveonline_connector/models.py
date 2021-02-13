

from esipy import EsiClient, EsiSecurity, EsiApp
from django.core.cache import cache
from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User, Group
from django.utils.dateparse import parse_datetime
from django.apps import apps
from django_singleton_admin.models import DjangoSingleton
from django_eveonline_connector.exceptions import EveMissingScopeException
import datetime
import logging
import json
import traceback
import pyswagger
from django.db.models import Q
logger = logging.getLogger(__name__)
app_config = apps.get_app_config('django_eveonline_connector')

id_types = (
    ("character", "character"),
    ("corporation", "corporation"),
    ("alliance", "alliance"),
)

"""
ESI Models
These models are used as wrappers around EsiPy
"""


class EveClient(DjangoSingleton):
    esi_base_url = models.URLField(
        default="https://esi.evetech.net/latest/swagger.json?datasource=tranquility")
    esi_callback_url = models.URLField()
    esi_client_id = models.CharField(max_length=255)
    esi_secret_key = models.CharField(max_length=255)

    def save(self, *args, **kwargs):
        try:
            keys = cache.keys('esi_sso_url*')

            for key in keys:
                cache.delete(key)
        except Exception as e:
            logger.error("Error clearing cache for ESI SSO URL keys: %s" + e)

        super(EveClient, self).save(*args, **kwargs)

    def __str__(self):
        return str({
            'esi_base_url': self.esi_base_url,
            'esi_callback_url': self.esi_callback_url,
            'esi_client_id': self.esi_client_id
        })

    def as_dict(self):
        return {
            'esi_base_url': self.esi_base_url,
            'esi_callback_url': self.esi_callback_url,
            'esi_client_id': self.esi_client_id
        }

    def get_sso_url(self, extra_scopes=[]):
        """
        Expects a list of scope names 
        e.g ['esi.scope.v1', 'esi.scope.v2']
        """
        scope_list = EveScope.convert_to_list(EveScope.objects.filter(
            Q(required=True) |
            Q(name__in=extra_scopes)
        ))
        scope_string = ",".join(scope_list)
        scope_string = f"esi_sso_url:{scope_string}"
        if scope_string in cache:
            return cache.get(scope_string)
        else:
            esi_sso_url = EsiSecurity(
                client_id=self.esi_client_id,
                redirect_uri=self.esi_callback_url,
                secret_key=self.esi_secret_key,
                headers={'User-Agent': "Krypted Platform"}
            ).get_auth_uri(scopes=scope_list,
                           state=self.esi_client_id)
            cache.set(scope_string, esi_sso_url, timeout=86400)
            return esi_sso_url

    @staticmethod
    def call(op, raise_exception=False, **kwargs):
        operation = EveClient.get_esi_app().op[op]
        # Pull the required scopes from the ESI Swagger Definition
        required_scopes = set()
        if operation.security:
            for definition in operation.security:
                if 'evesso' in definition:
                    for scope_name in definition['evesso']:
                        scope_creation = EveScope.objects.get_or_create(
                            name=scope_name)
                        scope = scope_creation[0]
                        if scope_creation[1]:
                            logger.error(
                                "Encountered unknown scope '%s', please notify Krypted developers." % scope)
                        required_scopes.add(scope)

        # Find the token with proper scopes and access
        if required_scopes:
            if 'token' in kwargs:
                token = kwargs.get('token')
                for scope in required_scopes:
                    if scope not in token.scopes.all():
                        raise EveMissingScopeException(
                            f"EveClient was passed a token that is missing the required scopes: {scope}")

            elif 'character_id' in kwargs:
                try:
                    token = EveToken.objects.get(evecharacter__external_id=kwargs.get(
                        'character_id'), scopes__in=required_scopes)
                except EveToken.DoesNotExist as e:
                    raise EveMissingScopeException(
                        f"EveClient was passed a character_id that does not have the proper token: {required_scopes}")
            elif 'corporation_id' in kwargs:
                eve_corporation = EveCorporation.objects.get(
                    external_id=kwargs.get('corporation_id'))

                if not eve_corporation.ceo:
                    raise EveMissingScopeException(
                        'EveClient was passed a corporation_id that does not have a CEO')

                try:
                    token_pk = eve_corporation.ceo.token.pk
                    token = EveToken.objects.get(
                        pk=token_pk, scopes__in=required_scopes)
                except EveToken.DoesNotExist as e:
                    raise EveMissingScopeException(
                        'EveClient was passed a corporation_id that does not have the proper CEO token')

            else:
                raise Exception(
                    "Attempted to make protected EsiCall without valid token or auto-matching keyword argument")
        else:
            token = None

        if token:
            if token.refresh():
                logger.info(
                    f"Calling token guarded ESI: {op} with arguments {kwargs}")

                request = EveClient.get_esi_client(token=token).request(
                    operation(**kwargs), raise_on_error=raise_exception)
            else:
                logger.info(
                    f"Skipping ESI call for expired token: {op} with arguments {kwargs}")

        else:
            logger.info(f"Calling ESI: {op} with arguments {kwargs}")
            request = EveClient.get_esi_client().request(
                operation(**kwargs), raise_on_error=raise_exception)

        if request.status not in [200, 204, 503, 504]:
            logger.warning(
                f"Failed ({request.status}) ESI call '{op}' with {kwargs}. Response: {request.data}")

        return request

    @staticmethod
    def get_required_scopes(op):
        operation = EveClient.get_esi_app().op[op]
        # Pull the required scopes from the ESI Swagger Definition
        required_scopes = set()
        if operation.security:
            for definition in operation.security:
                if 'evesso' in definition:
                    for scope_name in definition['evesso']:
                        scope_creation = EveScope.objects.get_or_create(
                            name=scope_name)
                        scope = scope_creation[0]
                        if scope_creation[1]:
                            logger.error(
                                "Encountered unknown scope '%s', please notify Krypted developers." % scope)
                        required_scopes.add(scope)
        return required_scopes

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
        try:
            if 'esi_app' in cache:
                return cache.get('esi_app')
        except Exception:
            esi_app = EsiApp(cache_time=86400).get_latest_swagger
            try:
                cache.set('esi_app', esi_app, timeout=86400)
            except Exception:
                logger.exception("Failed to store ESI Application in cache")
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

# TODO: remove type, all scopes added.. add scopes via fixtures


class EveScope(models.Model):
    name = models.CharField(unique=True, max_length=128)
    required = models.BooleanField(default=False)

    def __str__(self):
        return self.name

    @staticmethod
    def convert_to_list(scopes):
        return [scope.name for scope in scopes]

    @staticmethod
    def convert_to_string(scopes):
        return ",".join([scope.name for scope in scopes])

    @staticmethod
    def get_required():
        return EveScope.objects.filter(required=True)


class EveToken(models.Model):
    access_token = models.TextField()
    refresh_token = models.TextField()
    expires_in = models.IntegerField(default=0)
    expiry = models.DateTimeField(auto_now_add=True)
    invalidated = models.DateTimeField(blank=True, null=True, default=None)
    scopes = models.ManyToManyField("EveScope", blank=True)
    requested_scopes = models.ManyToManyField(
        "EveScope", blank=True, related_name="requested_scopes", default=EveScope.get_required)
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="eve_tokens", null=True)

    def __str__(self):
        try:
            return "<%s:%s>" % (self.evecharacter.name, self.user)
        except Exception as e:
            return "<%s:%s>" % ("Unknown Character", self.user)

    @property
    def valid(self):
        for scope in self.requested_scopes.all():
            if scope not in self.scopes.all():
                return False

        for scope in EveScope.objects.filter(required=True):
            if scope not in self.scopes.all():
                return False

        if self.invalidated:
            return False
        return True

    def refresh(self):
        esi_security = EveClient.get_esi_security()
        esi_security.update_token(self.populate())

        try:
            new_token = esi_security.refresh()
        except Exception as e:
            if b"invalid_grant" in e.response:
                if not self.invalidated:
                    self.invalidated = timezone.now()
                    self.save()
                return False

        if timezone.now() > self.expiry:
            if self.invalidated:
                self.invalidated = None
            self.access_token = new_token['access_token']
            self.refresh_token = new_token['refresh_token']
            self.expiry = timezone.now() + datetime.timedelta(0,
                                                              new_token['expires_in'])
            self.save()
            return True
        else:
            logger.info("Token refresh not needed")
            return True

    def populate(self):
        data = {}
        data['access_token'] = self.access_token
        data['refresh_token'] = self.refresh_token
        data['expires_in'] = self.expires_in

        return data

# fmt: off 
from django_eveonline_connector.utilities.static.universe import *
from django_eveonline_connector.utilities.esi.universe import *
# fmt: on

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
    roles = models.ManyToManyField("EveCorporationRole", blank=True)
    token = models.OneToOneField(
        "EveToken", on_delete=models.CASCADE, null=True, blank=True)

    @staticmethod
    def get_primary_character(user):
        primary_character_obj = PrimaryEveCharacterAssociation.objects.filter(
            user=user).first()
        if primary_character_obj:
            return primary_character_obj.character
        else:
            return None

    @property
    def avatar(self):
        return "https://%s/characters/%s/%s" % (
            app_config.EVEIMG_CONFIG['domain'],
            self.external_id,
            app_config.EVEIMG_CONFIG['portrait_mapping']['character'],
        )

    @staticmethod
    def create_from_external_id(external_id):
        response = EveClient.call(
            'get_characters_character_id', character_id=external_id)

        eve_character = EveCharacter(
            name=response.data['name'],
            external_id=external_id)

        eve_character.save()

        return eve_character

    def update_character_corporation(self, corporation_id=None):
        if not corporation_id:
            try:
                response = EveClient.call(
                    'post_characters_affiliation', characters=[self.external_id])
                corporation_id = response.data[0]['corporation_id']
            except Exception as e:
                logger.error(
                    f"Error pulling corporation for character. Error: {e}. Response: {response.data}")

        if EveCorporation.objects.filter(external_id=corporation_id).exists():
            self.corporation = EveCorporation.objects.get(
                external_id=corporation_id)
        else:
            self.corporation = EveCorporation.create_from_external_id(
                external_id=corporation_id)

        self.save()

    class Meta:
        permissions = [
            ('view_corporation_characters',
             'Can view characters of same corporation'),
            ('view_alliance_characters', 'Can view characters of same alliance'),
            ('view_all_characters', 'Can view all characters')
        ]


class EveCorporation(EveEntity):
    ceo = models.OneToOneField(
        "EveCharacter", blank=True, null=True, on_delete=models.SET_NULL)
    ticker = models.CharField(max_length=5)
    alliance = models.ForeignKey(
        "EveAlliance", blank=True, null=True, on_delete=models.SET_NULL)

    track_corporation = models.BooleanField(default=False)
    track_characters = models.BooleanField(default=False)

    @staticmethod
    def create_from_external_id(external_id):
        response = EveClient.call(
            'get_corporations_corporation_id', corporation_id=external_id)
        eve_corporation = EveCorporation(
            name=response.data['name'],
            ticker=response.data['ticker'],
            external_id=external_id)

        eve_corporation.save()

        return eve_corporation

    def validate_ceo(self):
        valid = True
        required_scopes = ['esi-contracts.read_corporation_contracts.v1',
                           'esi-corporations.read_structures.v1', 'esi-corporations.read_corporation_membership.v1']
        scopes = EveScope.objects.filter(name__in=required_scopes)
        for scope in scopes:
            if scope not in self.ceo.token.scopes.all():
                self.ceo.token.requested_scopes.add(scope)
                valid = False

        return valid

    def save(self, *args, **kwargs):
        required_scopes = ['esi-contracts.read_corporation_contracts.v1',
                           'esi-corporations.read_structures.v1', 'esi-corporations.read_corporation_membership.v1']
        scopes = EveScope.objects.filter(name__in=required_scopes)
        if self.track_corporation and self.ceo:
            if not self.validate_ceo():
                self.track_corporation = False
                super(EveCorporation, self).save(*args, **kwargs)
                raise EveMissingScopeException(
                    f"CEO missing the requested scopes to enable corporation tracking. Please update token for {self.ceo}.")
        elif self.track_corporation and not self.ceo:
            from django_eveonline_connector.tasks import update_corporation_ceo
            update_corporation_ceo.apply_async(args=[self.external_id])
            self.track_corporation = False
            super(EveCorporation, self).save(*args, **kwargs)
            raise EveMissingScopeException(
                f"Unable to track a corporation without a CEO. Queued corporation update job for {self.external_id}.")

        super(EveCorporation, self).save(*args, **kwargs)


class EveAlliance(EveEntity):
    executor = models.OneToOneField(
        "EveCorporation", blank=True, null=True, on_delete=models.SET_NULL)
    ticker = models.CharField(max_length=5)

    def save(self, *args, **kwargs):
        super(EveAlliance, self).save(*args, **kwargs)

    @staticmethod
    def create_from_external_id(external_id):
        response = EveClient.call(
            'get_alliances_alliance_id', alliance_id=external_id)

        eve_alliance = EveAlliance(
            name=response.data['name'],
            ticker=response.data['ticker'],
            external_id=external_id)

        eve_alliance.save()

        return eve_alliance


"""
Entity Data Models 
These models represent entity data. 
"""


class EveEntityData(models.Model):
    entity = models.ForeignKey(EveEntity, on_delete=models.CASCADE)

    @classmethod
    def create_from_esi_row(cls, data_row, entity_external_id, *args, **kwargs):
        """
        Wrapper function around self._create_from_esi_row, which is defined by the extending class. 
        Converts the data from a single ESI row (e.g jump_clones = []) into a Django Model and saves it.
        """
        try:
            db_object = cls._create_from_esi_row(
                data_row, entity_external_id, *args, **kwargs)
            db_object.entity = EveEntity.objects.get(
                external_id=entity_external_id)
            db_object.save()
        except Exception as e:
            message = (
                f"Failed to create {cls.__name__} from ESI data row: {data_row}.\n"
                f"Failed for entity {entity_external_id}\n"
            )
            logger.warning(message)
            logger.error(e, exc_info=True)

    @staticmethod
    def _create_from_esi_row(data_row, entity_external_id, *args, **kwargs):
        raise NotImplementedError

    @classmethod
    def create_from_esi_response(cls, data, entity_external_id, *args, **kwargs):
        """
        Pre-processes the response from an ESI Call and generated Django database objects using cls.create_from_esi_row()
        Wrapper around self._create_esi_response, which is defined by the extending class. 
        """
        try:
            processed_data = cls._create_from_esi_response(
                data, entity_external_id, *args, **kwargs)
        except Exception as e:
            logger.warning(
                "Failed to process ESI response for %s. Data: %s" % (cls.__name__, data))
            logger.exception(e)

    @staticmethod
    def _create_from_esi_response(data, entity_external_id, *args, **kwargs):
        raise NotImplementedError

    class Meta:
        abstract = True


class EveAsset(EveEntityData):
    # ESI Data
    is_blueprint_copy = models.BooleanField()
    is_singleton = models.BooleanField()
    item_id = models.BigIntegerField()
    location_flag = models.CharField(max_length=64)
    location_id = models.BigIntegerField()
    location_type = models.CharField(max_length=64)
    quantity = models.IntegerField()
    type_id = models.IntegerField()

    # Mapped Static Data
    group_id = models.IntegerField()
    category_id = models.IntegerField()

    # Our Conversions
    item_name = models.CharField(max_length=255)  # typeName
    item_type = models.CharField(max_length=32)  # categoryName
    location_name = models.CharField(max_length=128)

    def __str__(self):
        return "<%s :: %s - %s>" % (self.entity, self.item_name, self.location_name)

    @staticmethod
    def get_bad_asset_category_ids():
        """
        Assets have some very ugly categories that can't be resolved to locations. e.g POCOs
        It's recommended that you just filter out assets in these categories.
        """
        return app_config.ESI_BAD_ASSET_CATEGORIES

    @staticmethod
    def _create_from_esi_response(data, entity_external_id, *args, **kwargs):
        for row in data:
            EveAsset.create_from_esi_row(row, entity_external_id)

    @staticmethod
    def _create_from_esi_row(data_row, entity_external_id, *args, **kwargs):
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

        if asset.category_id in EveAsset.get_bad_asset_category_ids():
            asset.location_name = "Unresolved Location"
            return asset  # skip resolving of location

        # Location IDs suck to resolve, we must do different things for each type
        if asset.location_flag == "Hangar":
            asset.location_name = resolve_location_from_location_id_location_type(
                asset.location_id,
                asset.location_type,
                entity_external_id)

        return asset


class EveJumpClone(EveEntityData):
    # ESI Data
    location_id = models.BigIntegerField()
    location_type = models.CharField(max_length=64)
    jump_clone_id = models.IntegerField()

    # Our Conversions
    location = models.CharField(max_length=128)
    implants = models.TextField()

    @staticmethod
    def _create_from_esi_response(data, entity_external_id, *args, **kwargs):
        for row in data['jump_clones']:
            EveJumpClone.create_from_esi_row(row, entity_external_id)

    @staticmethod
    def _create_from_esi_row(data_row, entity_external_id, *args, **kwargs):
        """
        URL: /characters/{character_id}/clones/
        Expects a row from `jump_clones`
        """
        clone = EveJumpClone(
            location_id=data_row['location_id'],
            location_type=data_row['location_type'],
            jump_clone_id=data_row['jump_clone_id'],)

        logger.debug(data_row)
        clone.location = resolve_location_from_location_id_location_type(
            clone.location_id,
            clone.location_type,
            entity_external_id)

        implants = []
        for implant in data_row['implants']:
            implants.append(resolve_type_id_to_type_name(implant))

        clone.implants = ",".join(implants)
        return clone


class EveContact(EveEntityData):
    # ESI Data
    contact_id = models.IntegerField()
    is_blocked = models.BooleanField(default=False)
    is_watched = models.BooleanField(default=False)
    label_ids = models.TextField(blank=True, null=True)
    standing = models.FloatField()

    # Our Conversions
    contact_name = models.CharField(max_length=64)
    contact_type = models.CharField(max_length=32, choices=id_types)

    @property
    def evewho(self):
        return "https://%s/%s/%s" % (app_config.EVEWHO_CONFIG['domain'],
                                     self.contact_type,
                                     self.contact_id)

    @property
    def portrait(self):
        return "https://%s/%ss/%s" % (app_config.EVEIMG_CONFIG['domain'],
                                      self.contact_type,
                                      app_config.EVEIMG_CONFIG['portrait_mapping'][self.contact_type])

    @staticmethod
    def _create_from_esi_response(data, entity_external_id, *args, **kwargs):
        if len(data) == 0:
            return  # no contacts
        # process user ids
        contact_ids_to_resolve = set()
        for contact in data:
            contact_ids_to_resolve.add(contact['contact_id'])
        contact_names = resolve_ids(list(contact_ids_to_resolve))
        for row in data:
            EveContact.create_from_esi_row(
                row, entity_external_id, contact_name=contact_names[row['contact_id']])

    @staticmethod
    def _create_from_esi_row(data_row, entity_external_id, *args, **kwargs):
        # Store what ESI returns
        contact = EveContact(
            contact_id=data_row['contact_id'],
            contact_type=data_row['contact_type'],
            standing=data_row['standing'],
            is_blocked=data_row.get('is_blocked', False),
            is_watched=data_row.get('is_watched', False),
        )

        # Handle optional ESI fields
        if 'label_ids' in data_row:
            label_ids = []
            for label_id in data_row['label_ids']:
                label_ids.append(str(label_id))
            if len(label_ids) >= 1:
                contact.label_ids = ",".join(label_ids)

        # Our Conversions
        if 'contact_name' not in kwargs:
            logger.warning(
                "Called without contact_name keyword argument. Performance decrease.")
            contact.contact_name = resolve_ids([data_row['contact_id']])[
                contact.contact_id]
        else:
            contact.contact_name = kwargs.get('contact_name')
        return contact


class EveContract(EveEntityData):
    # ESI Data
    contract_id = models.BigIntegerField(unique=True)
    acceptor_id = models.BigIntegerField()
    assignee_id = models.BigIntegerField()

    buyout = models.FloatField(blank=True, null=True)
    collateral = models.FloatField(blank=True, null=True)
    price = models.FloatField(blank=True, null=True)
    reward = models.FloatField(blank=True, null=True)
    volume = models.FloatField(blank=True, null=True)

    date_accepted = models.DateTimeField(blank=True, null=True)
    date_completed = models.DateTimeField(blank=True, null=True)
    date_expired = models.DateTimeField()
    date_issued = models.DateTimeField()
    days_to_complete = models.IntegerField(blank=True, null=True)

    for_corporation = models.BooleanField()
    availability = models.CharField(max_length=32)
    issuer_corporation_id = models.BigIntegerField()
    issuer_id = models.BigIntegerField()

    start_location_id = models.BigIntegerField(blank=True, null=True)
    end_location_id = models.BigIntegerField(blank=True, null=True)
    status = models.CharField(max_length=32)
    title = models.TextField(blank=True, null=True)
    type = models.CharField(max_length=16)

    # Our Conversions
    acceptor_name = models.CharField(max_length=64)
    assignee_name = models.CharField(max_length=64)
    issuer_name = models.CharField(max_length=64)
    issuer_corporation_name = models.CharField(max_length=255)
    acceptor_type = models.CharField(max_length=32, choices=id_types)
    assignee_type = models.CharField(max_length=32, choices=id_types)
    issuer_type = models.CharField(max_length=64, choices=id_types)
    items = models.TextField(null=True)

    @staticmethod
    def _create_from_esi_response(data, entity_external_id, *args, **kwargs):
        ids_to_resolve = set()
        for contract in data:
            ids_to_resolve.add(contract['acceptor_id'])
            ids_to_resolve.add(contract['assignee_id'])
            ids_to_resolve.add(contract['issuer_id'])
            ids_to_resolve.add(contract['issuer_corporation_id'])
        resolved_ids = resolve_ids_with_types(ids_to_resolve)

        for row in data:
            EveContract.create_from_esi_row(
                row, entity_external_id, resolved_ids=resolved_ids, corporation=False)

    @staticmethod
    def _create_from_esi_row(data_row, entity_external_id, *args, **kwargs):
        """
        Fill an EveContract object according to the provided ESI data row.

        **Args**
            **data_row** (``dict``)
                The ESI data row that represents this object 
            **entity_external_id** (``int``)
                The External ID for the EveEntity

        **Kwargs**
            **resolved_ids** (``list``)
                Pre-resolved IDs for assignees, acceptors, etc. 
            **corporation** (``boolean``)
                If set, assumes we are resolving corporation contract items.

        **Returns**
            EveContract() instance
        """
        contract_id = data_row['contract_id']
        if EveContract.objects.filter(contract_id=contract_id).exists():
            contract = EveContract.objects.get(contract_id=contract_id)
            update = True
        else:
            contract = EveContract()
            update = False

        for key in data_row.keys():
            try:
                if type(data_row[key]) == pyswagger.primitives._time.Datetime:
                    data_row[key] = data_row[key].to_json()
                setattr(contract, str(key), data_row[key])
            except AttributeError:
                logger.error(
                    f"Encountered unknown attribute {key} for EveContract")

        if update:
            return contract  # the other fields will already be sorted out if we're doing an update

        if not 'resolved_ids' in kwargs:
            logger.warning(
                "Resolved IDs were not passed. Performance decrease.")
            ids_to_resolve = [contract.acceptor_id, contract.assignee_id,
                              contract.issuer_id, contract.issuer_corporation_id]
            resolved_ids = resolve_ids_with_types(ids_to_resolve)
            # todo resolve IDs
        else:
            resolved_ids = kwargs.get('resolved_ids')

        contracts_response = EveClient.call(
            'get_characters_character_id_contracts_contract_id_items',
            character_id=entity_external_id, contract_id=contract.contract_id)

        if not contracts_response:
            items = None
        else:
            items = []
            for item in contracts_response.data:
                items.append("%s %s" % (
                    item['quantity'], resolve_type_id_to_type_name(item['type_id'])))
            contract.items = "\n".join(items)

        contract.acceptor_name = resolved_ids[contract.acceptor_id]['name']
        contract.assignee_name = resolved_ids[contract.assignee_id]['name']
        contract.issuer_name = resolved_ids[contract.issuer_id]['name']
        contract.acceptor_type = resolved_ids[contract.acceptor_id]['type']
        contract.assignee_type = resolved_ids[contract.assignee_id]['type']
        contract.issuer_type = resolved_ids[contract.issuer_id]['type']
        contract.issuer_corporation_name = resolved_ids[contract.issuer_corporation_id]

        return contract


class EveSkill(EveEntityData):
    # ESI Data
    active_skill_level = models.IntegerField()
    trained_skill_level = models.IntegerField()
    skill_id = models.IntegerField()
    skillpoints_in_skill = models.IntegerField()

    # Our Conversions
    skill_name = models.CharField(max_length=64)
    skill_group = models.CharField(max_length=64)

    class Meta:
        unique_together = ['entity', 'skill_name']

    @staticmethod
    def _create_from_esi_response(data, entity_external_id, *args, **kwargs):
        for row in data.skills:
            EveSkill.create_from_esi_row(row, entity_external_id)

    @staticmethod
    def _create_from_esi_row(data_row, entity_external_id, *args, **kwargs):
        skill = EveSkill(
            active_skill_level=data_row['active_skill_level'],
            trained_skill_level=data_row['trained_skill_level'],
            skill_id=data_row['skill_id'],
            skillpoints_in_skill=data_row['skillpoints_in_skill'],
        )

        skill.skill_name = resolve_type_id_to_type_name(data_row['skill_id'])
        skill.skill_group = resolve_type_id_to_group_name(data_row['skill_id'])

        return skill


class EveJournalEntry(EveEntityData):
    # ESI Data
    external_id = models.BigIntegerField(unique=True)
    amount = models.FloatField(blank=True, null=True)
    balance = models.FloatField(blank=True, null=True)
    tax = models.FloatField(blank=True, null=True)
    tax_receiver_id = models.IntegerField(blank=True, null=True)
    context_id = models.BigIntegerField(blank=True, null=True)
    context_id_type = models.CharField(max_length=32, blank=True, null=True)
    date = models.DateTimeField()
    description = models.TextField()
    reason = models.TextField()
    ref_type = models.CharField(max_length=128)
    first_party_id = models.IntegerField(blank=True, null=True)
    second_party_id = models.IntegerField(blank=True, null=True)

    # Our Conversions
    first_party_name = models.CharField(max_length=64)
    first_party_type = models.CharField(max_length=32, choices=id_types)
    second_party_name = models.CharField(max_length=64)
    second_party_type = models.CharField(max_length=32, choices=id_types)

    @staticmethod
    def _create_from_esi_response(data, entity_external_id, *args, **kwargs):
        ids_to_resolve = set()
        for row in data:
            ids_to_resolve.add(row['first_party_id'])
            ids_to_resolve.add(row['second_party_id'])
        resolved_ids = resolve_ids_with_types(ids_to_resolve)

        for row in data:
            if EveJournalEntry.objects.filter(external_id=row['id']).exists():
                continue
            EveJournalEntry.create_from_esi_row(
                row, entity_external_id, resolved_ids=resolved_ids)

    @staticmethod
    def _create_from_esi_row(data_row, entity_external_id, *args, **kwargs):
        entry = EveJournalEntry(
            external_id=data_row['id'],
            date=parse_datetime(data_row['date'].to_json()),
            description=data_row['description'],
            reason=data_row['description'],
            ref_type=data_row['ref_type'],
            amount=data_row.get('amount', None),
            balance=data_row.get('balance', None),
            tax=data_row.get('tax', None),
            tax_receiver_id=data_row.get('tax_receiver_id', None),
            context_id=data_row.get('context_id', None),
            context_id_type=data_row.get('context_id_type', None),
            first_party_id=data_row.get('first_party_id', None),
            second_party_id=data_row.get('second_party_id', None),
        )

        if 'resolved_ids' not in kwargs:
            logger.warning(
                "Called without Resolved IDs. Performance decrease.")
            ids_to_resolve = [entry.first_party_id, entry.second_party_id]
            resolved_ids = resolved_ids_with_types(ids_to_resolve)
        else:
            resolved_ids = kwargs.get('resolved_ids')

        entry.first_party_name = resolved_ids[entry.first_party_id]['name']
        entry.first_party_type = resolved_ids[entry.first_party_id]['type']
        entry.second_party_name = resolved_ids[entry.second_party_id]['name']
        entry.second_party_type = resolved_ids[entry.second_party_id]['type']

        return entry


class EveTransaction(EveEntityData):
    # ESI Data
    client_id = models.IntegerField()
    date = models.DateTimeField()
    is_buy = models.BooleanField()
    is_personal = models.BooleanField()
    journal_ref_id = models.BigIntegerField()
    location_id = models.BigIntegerField()
    quantity = models.IntegerField()
    transaction_id = models.BigIntegerField(unique=True)
    type_id = models.IntegerField()
    unit_price = models.FloatField()

    # Our Conversions
    client_name = models.CharField(max_length=64)
    client_type = models.CharField(max_length=64, choices=id_types)
    location_name = models.CharField(max_length=128)
    item_name = models.CharField(max_length=255)

    @property
    def get_journal_entry(self):
        if EveJournalEntry.objects.filter(external_id=self.journal_ref_id).exists():
            return EveJournalEntry.objects.get(external_id=self.journal_ref_id)
        return None

    @staticmethod
    def _create_from_esi_response(data, entity_external_id, *args, **kwargs):
        ids_to_resolve = set()
        for row in data:
            ids_to_resolve.add(row['client_id'])
        resolved_ids = resolve_ids_with_types(ids_to_resolve)

        for row in data:
            if EveTransaction.objects.filter(transaction_id=row['transaction_id']):
                continue
            EveTransaction.create_from_esi_row(
                row, entity_external_id, resolved_ids=resolved_ids)

    @staticmethod
    def _create_from_esi_row(data_row, entity_external_id, *args, **kwargs):
        transaction = EveTransaction(
            client_id=data_row['client_id'],
            date=parse_datetime(data_row['date'].to_json()),
            is_buy=data_row['is_buy'],
            is_personal=data_row['is_personal'],
            journal_ref_id=data_row['journal_ref_id'],
            location_id=data_row['location_id'],
            quantity=data_row['quantity'],
            transaction_id=data_row['transaction_id'],
            type_id=data_row['type_id'],
            unit_price=data_row['unit_price'],
        )

        if 'resolved_ids' not in kwargs:
            logger.warning(
                "Called without Resolved IDs. Performance decrease.")
            ids_to_resolve = [transaction.client_id]
            resolved_ids = resolved_ids_with_types(ids_to_resolve)
        else:
            resolved_ids = kwargs.get('resolved_ids')

        transaction.client_name = resolved_ids[transaction.client_id]['name']
        transaction.client_type = resolved_ids[transaction.client_id]['type']
        transaction.item_name = resolve_type_id_to_type_name(
            transaction.type_id)

        try:
            transaction.location_name = resolve_location_from_location_id_location_type(
                transaction.location_id, 'station', entity_external_id)
        except Exception as e:
            transaction.location_name = resolve_location_from_location_id_location_type(
                transaction.location_id, 'other', entity_external_id)

        if not transaction.location_name:
            transaction.location_name = "Unknown Location"

        return transaction


"""
Other EVE Models
"""


class EveStructure(EveEntityData):
    # Base ESI Data
    corporation_id = models.BigIntegerField()
    fuel_expires = models.DateTimeField(null=True, blank=True)
    next_reinforce_apply = models.DateTimeField(null=True, blank=True)
    next_reinforce_hour = models.BigIntegerField(null=True, blank=True)
    next_reinforce_weekday = models.BigIntegerField(null=True, blank=True)
    profile_id = models.BigIntegerField()
    reinforce_hour = models.BigIntegerField()
    reinforce_weekday = models.BigIntegerField(null=True, blank=True)
    services = models.TextField(null=True, blank=True)
    state = models.CharField(max_length=64)
    state_timer_end = models.DateTimeField(null=True, blank=True)
    state_timer_start = models.DateTimeField(null=True, blank=True)
    structure_id = models.BigIntegerField()
    system_id = models.BigIntegerField()
    type_id = models.BigIntegerField()
    unanchors_at = models.DateTimeField(null=True, blank=True)

    # Additional ESI Data
    owner_id = models.BigIntegerField()
    solar_system_id = models.BigIntegerField()
    type_id = models.BigIntegerField(null=True, blank=True)
    name = models.CharField(max_length=256)

    @property
    def fuel_expires_soon(self):
        if self.fuel_expires and ((self.fuel_expires - timezone.now()).days < 7):
            return True
        return False

    @property
    def reinforcement_time(self):
        return timezone.now().replace(hour=0, minute=0, second=0,
                                      microsecond=0) + datetime.timedelta(hours=self.reinforce_hour)

    def __str__(self):
        if not self.name:
            self.name = "Unknown Name"
        return f"{self.name}"

    @staticmethod
    def _create_from_esi_response(data, entity_external_id, *args, **kwargs):
        for row in data:
            EveStructure.create_from_esi_row(row, entity_external_id)

    @staticmethod
    def _create_from_esi_row(data_row, entity_external_id, *args, **kwargs):
        logger.info("Creating EVE Structure")
        if EveStructure.objects.filter(structure_id=data_row['structure_id']).exists():
            structure = EveStructure.objects.filter(
                structure_id=data_row['structure_id']).first()
        else:
            structure = EveStructure()
        for key in data_row.keys():
            try:
                if type(data_row[key]) == pyswagger.primitives._time.Datetime:
                    data_row[key] = data_row[key].to_json()
                setattr(structure, str(key), data_row[key])
            except AttributeError:
                logger.error(
                    f"Encountered unknown attribute {key} for EveStructure")

        additional_info = get_structure(
            data_row['structure_id'], entity_external_id).data

        for key in additional_info.keys():
            try:
                setattr(structure, str(key), additional_info[key])
            except AttributeError:
                logger.error(
                    f"Encountered unknown attribute {key} for EveStructure")

        return structure

    class Meta:
        permissions = [
            ('bypass_corporation_view_requirements',
             "Can view a corporation's structures regardless of current membership"),
        ]


"""
Static EVE Models
These represent static EVE models that we need associations for.
"""


class EveCorporationRole(models.Model):
    codename = models.CharField(max_length=64, unique=True)
    name = models.CharField(max_length=64, unique=True)

    def __str__(self):
        return self.name


"""
EVE Connector Models
Models for EVE Connector functionality 
"""


class PrimaryEveCharacterAssociation(models.Model):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="primary_evecharacter")
    character = models.OneToOneField(
        EveCharacter, on_delete=models.CASCADE, related_name="primary_to")

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

    def get_related_characters(self):
        return EveCharacter.objects.filter(token__in=EveToken.objects.filter(user=self.user)).exclude(external_id=self.character.external_id)


class EveCharacterInfo(models.Model):
    # TODO: Merge this into EveCharacter
    character = models.OneToOneField(
        EveCharacter, on_delete=models.CASCADE, related_name="info")

    # game info
    skill_points = models.IntegerField(blank=True, null=True)
    net_worth = models.FloatField(blank=True, null=True)

    # update statistics
    assets_last_updated = models.DateTimeField(blank=True, null=True)
    jump_clones_last_updated = models.DateTimeField(blank=True, null=True)
    contacts_last_updated = models.DateTimeField(blank=True, null=True)
    contracts_last_updated = models.DateTimeField(blank=True, null=True)
    skills_last_updated = models.DateTimeField(blank=True, null=True)
    journal_last_updated = models.DateTimeField(blank=True, null=True)
    transactions_last_updated = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return self.character.name


class EveGroupRule(models.Model):
    group = models.OneToOneField(Group, on_delete=models.CASCADE)
    include_alts = models.BooleanField(default=True)

    # qualifiers
    characters = models.ManyToManyField("EveCharacter", blank=True)
    corporations = models.ManyToManyField("EveCorporation", blank=True)
    alliances = models.ManyToManyField("EveAlliance", blank=True)
    roles = models.ManyToManyField("EveCorporationRole", blank=True)

    @property
    def current_user_list(self):
        return User.objects.filter(group__contains=self.group)

    @property
    def valid_user_list(self):
        django_filter = Q()
        if self.characters.all():
            django_filter &= Q(evecharacter__in=self.characters.all())
        if self.corporations.all():
            django_filter &= Q(
                evecharacter__corporation__in=self.corporations.all())
        if self.alliances.all():
            django_filter &= Q(
                evecharacter__corporation__alliance__in=self.alliances.all())
        if self.roles.all():
            django_filter &= Q(evecharacter__roles__in=self.roles.all())
        if not self.include_alts:
            django_filter &= ~Q(evecharacter__primary_to=None)
        if django_filter != Q():
            return User.objects.filter(eve_tokens__in=EveToken.objects.filter(django_filter))
        else:
            return User.objects.none()

    @property
    def missing_user_list(self):
        return self.valid_user_list.filter(~Q(groups=self.group))

    @property
    def invalid_user_list(self):
        django_filter = Q()
        if self.characters.all():
            django_filter &= Q(evecharacter__in=self.characters.all())
        if self.corporations.all():
            django_filter &= Q(
                evecharacter__corporation__in=self.corporations.all())
        if self.alliances.all():
            django_filter &= Q(
                evecharacter__corporation__alliance__in=self.alliances.all())
        if self.roles.all():
            django_filter &= Q(evecharacter__roles__in=self.roles.all())
        if not self.include_alts:
            django_filter &= ~Q(evecharacter__primary_to=None)
        if django_filter != Q():
            return User.objects.filter(groups=self.group).exclude(eve_tokens__in=EveToken.objects.filter(django_filter))
        else:
            return User.objects.none()
