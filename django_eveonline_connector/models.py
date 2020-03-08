from django.core.cache import cache
from esipy import EsiClient, EsiSecurity, EsiApp
from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from django.apps import apps
import datetime
import logging
import json
import traceback
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
            elif 'character_id' in kwargs:
                token = EveToken.objects.get(evecharacter__external_id=kwargs.get(
                    'character_id'), scopes__in=required_scopes)
            elif 'corporation_id' in kwargs:
                eve_corporation = EveCorporation.objects.get(
                    external_id=kwargs.get('corporation_id'))

                if not eve_corporation.ceo:
                    raise EveToken.DoesNotExist("Missing CEO Token with scopes %s for %s" % (
                        required_scopes, eve_corporation.external_id))

                token_pk = eve_corporation.ceo.token.pk
                token = EveToken.objects.get(
                    pk=token_pk, scopes__in=required_scopes)
            else:
                raise Exception(
                    "Attempted to make protected EsiCall without token or auto-matching keyword argument")
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
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="eve_tokens", null=True)

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
from django_eveonline_connector.utilities.esi.universe import *
from django_eveonline_connector.utilities.static.database_helpers import *

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
        response = EveClient.call(
            'get_characters_character_id', character_id=external_id)

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
        response = EveClient.call(
            'get_corporations_corporation_id', corporation_id=external_id)
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
            logger.warning("Failed to create %s from ESI data row: %s." % (
                cls.__name__, data_row))
            logger.exception(e)

    @staticmethod
    def _create_from_esi_row(data_row, entity_external_id, *args, **kwargs):
        raise NotImplementedError

    @classmethod
    def create_from_esi_response(cls, data, entity_external_id, *args, **kwargs):
        """
        Pre-processes the response from an ESI Call and generated Django database objects using cls.create_from_esi_row()
        Wrapper around self._process_esi_response, which is defined by the extending class. 
        """
        try:
            processed_data = cls._process_esi_response(data, *args, **kwargs)
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
    item_name = models.CharField(max_length=128)  # typeName
    item_type = models.CharField(max_length=32)  # categoryName
    location = models.CharField(max_length=128)

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
            EveAsset.create_from_esi_row(row)

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

        # Location IDs suck to resolve, we must do different things for each type
        asset.location = resolve_location_from_location_id_location_type(
            asset.location_id,
            asset.location_type,
            entity_external_id)

        return asset


class EveJumpClone(EveEntityData):
    # ESI Data
    location_id = models.IntegerField()
    location_type = models.CharField(max_length=64)
    jump_clone_id = models.IntegerField()

    # Our Conversions
    location = models.CharField(max_length=128)
    implants = models.TextField()

    @staticmethod
    def _process_esi_response(data, *args, **kwargs):
        for row in data:
            EveJumpClone.create_from_esi_row(row)

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
    label_ids = models.TextField()
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
        # process user ids
        contact_ids_to_resolve = set()
        for contact in data:
            contact_ids_to_resolve.add(contact['contact_id'])
        contact_names = resolve_ids(contact_ids_to_resolve)
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
                label_ids.append(label_id)
            contact.label_ids = ",".join(label_ids)

        # Our Conversions
        if 'contact_name' not in kwargs:
            logger.warning(
                "Called without contact_name keyword argument. Performance decrease.")
            contact.contact_name = resolve_id([contact.contact_id])[
                contact.contact_id]
        else:
            contact.contact_name = contact_name
        return contact


class EveContract(EveEntityData):
    # ESI Data
    contract_id = models.IntegerField(unique=True)
    acceptor_id = models.IntegerField()
    assignee_id = models.IntegerField()

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
    issuer_corporation_id = models.IntegerField()
    issuer_id = models.IntegerField()

    start_location_id = models.IntegerField(blank=True, null=True)
    end_location_id = models.IntegerField(blank=True, null=True)
    status = models.CharField(max_length=32)
    title = models.TextField(blank=True, null=True)
    type = models.CharField(max_length=16)

    # Our Conversions
    acceptor_name = models.CharField(max_length=64)
    assignee_name = models.CharField(max_length=64)
    issuer_name = models.CharField(max_length=64)
    issuer_corporation_name = models.CharField(max_length=64)
    acceptor_type = models.CharField(max_length=32, choices=id_types)
    assignee_type = models.CharField(max_length=32, choices=id_types)
    issuer_type = models.CharField(max_length=64, choices=id_types)
    items = models.TextField()

    @staticmethod
    def _create_from_esi_response(data, entity_external_id, *args, **kwargs):
        ids_to_resolve = set()
        for contract in data:
            ids_to_resolve.add(contract['acceptor_id'])
            ids_to_resolve.add(contract['assignee_id'])
            ids_to_resolve.add(contract['issuer_id'])
            ids_to_resolve.add(contract['issuer_corporation_id'])
        resolved_ids = resolve_ids(ids_to_resolve)

        for row in data:
            if 'for_corporation' in row and row['for_corporation']:
                corporation = EveCorporation.objects.filter(
                    external_id=row['issuer_corporation_id']).exclude(ceo=None).first()
                if corporation:
                    EveContract.create_from_esi_row(
                        row, corporation.external_id, token=token, corporation=True)
        else:
            EveContract.create_from_esi_row(
                row, entity_external_id, resolved_ids=resolved_ids, token=token, corporation=False)

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
        contract = EveContract(
            contract_id=data_row['contract_id'],
            acceptor_id=data_row['acceptor_id'],
            assignee_id=data_row['assignee_id'],
            buyout=data_row.get('buyout', None),
            collateral=data_row.get('collateral', None),
            price=data_row.get('price', None),
            reward=data_row.get('reward', None),
            volume=data_row.get('volume', None),
            date_accepted=parse_datetime(
                data_row['date_created'].to_json()) if 'date_created' in data_row else None,
            date_completed=parse_datetime(
                data_row['date_completed'].to_json()) if 'date_completed' in data_row else None,
            date_expired=parse_datetime(data_row['date_expired'].to_json()),
            date_issued=parse_datetime(data_row['date_issued'].to_json()),
            days_to_complete=data_row.get('days_to_complete', None),
            end_location_id=data_row.get('end_location_id', None),
            for_corporation=data_row['for_corporation'],
            issuer_corporation_id=data_row['issuer_corporation_id'],
            issuer_id=data_row['issuer_id'],
            start_location_id=data_row.get('start_location_id', None),
            status=data_row['status'],
            title=data_row.get('title', None),
            type=data_row['type'],

        )

        if not 'resolved_ids' in kwargs:
            logger.warning(
                "Resolved IDs were not passed. Performance decrease.")
            ids_to_resolve = [contract.acceptor_id, contract.assignee_id,
                              contract.issuer_id, contract.issuer_corporation_id]
            resolved_ids = resolve_ids(ids_to_resolve)
            # todo resolve IDs
        else:
            resolved_ids = kwargs.get('resolved_ids')

        if 'corporation' in kwargs and kwargs.get('corporation'):
            contracts_response = EveClient.call(
                'get_corporations_corporation_id_contracts_contract_id_items', token,
                corporation_id=entity_external_id, contract_id=contract_id)
        else:
            contracts_response = EveClient.call(
                'get_characters_character_id_contracts_contract_id_items', token,
                character_id=entity_external_id, contract_id=contract_id)

        items = []
        for item in contracts_response:
            items.append("%s %s" % (
                item['quantity'], resolve_type_id_to_type_name(item['type_id'])))
        contract.items = "\n".join(items)

        contract.acceptor_name = resolved_ids[contract.acceptor_id]['name']
        contract.assignee_name = resolved_ids[contract.assignee_name]['name']
        contract.issuer_name = resolved_ids[contract.issuer_name]['name']
        contract.acceptor_type = resolved_ids[contract.acceptor_id]['type']
        contract.assignee_type = resolved_ids[contract.assignee_name]['type']
        contract.issuer_type = resolved_ids[contract.issuer_name]['type']
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
        for row in data:
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
    external_id = models.IntegerField(unique=True)
    amount = models.FloatField(blank=True, null=True)
    balance = models.FloatField(blank=True, null=True)
    tax = models.FloatField(blank=True, null=True)
    tax_receiver_id = models.IntegerField(blank=True, null=True)
    context_id = models.IntegerField(blank=True, null=True)
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
        resolved_ids = resolve_ids(ids_to_resolve)

        for row in data:
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
            resolved_ids = resolve_ids(ids_to_resolve)
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
    journal_ref_id = models.IntegerField()
    location_id = models.IntegerField()
    quantity = models.IntegerField()
    transaction_id = models.IntegerField(unique=True)
    type_id = models.IntegerField()
    unit_price = models.FloatField()

    # Our Conversions
    client_name = models.CharField(max_length=64)
    client_type = models.CharField(max_length=64, choices=id_types)
    location_name = models.CharField(max_length=64)
    type_name = models.CharField(max_length=64)

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
        resolved_ids = resolve_ids(ids_to_resolve)

        for row in data:
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
            resolved_ids = resolve_ids(ids_to_resolve)
        else:
            resolved_ids = kwargs.get('resolved_ids')

        transaction.client_name = resolved_ids[transcation.client_id]['name']
        transaction.client_type = resolved_ids[transaction.client_id]['type']
        transaction.type_name = resolve_type_id_to_type_name(
            transaction.type_id)

        if resolve_location_from_location_id_location_type(location_id, 'station') == 'Unknown Location':
            transaction.location_name = resolve_location_from_location_id_location_type(
                location_id, 'other', entity_external_id)
        else:
            transaction.location_name = resolve_location_from_location_id_location_type(
                location_id, 'station', entity_external_id)

        return transaction


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
