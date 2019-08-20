from django.db import models
from django.core.cache import cache
from django.contrib.auth.models import User
from esipy import EsiClient, EsiSecurity, EsiApp

"""
OAuth Models
These models are used for the EVE Online token system
"""


class EveScope(models.Model):
    name = models.TextField()

    def __str__(self):
        return self.name


class EveClient(models.Model):
    esi_base_url = models.URLField(
        default="https://esi.evetech.net/latest/swagger.json?datasource=tranquility")
    esi_callback_url = models.URLField()
    esi_sso_url = models.URLField(editable=False)  # set on save
    esi_client_id = models.CharField(max_length=255)
    esi_secret_key = models.CharField(max_length=255)
    esi_scopes = models.ManyToManyField(
        "EveScope", blank=True)

    def save(self, *args, **kwargs):
        if EveClient.objects.all():
            EveClient.objects.all()[0].delete()

        super(EveClient, self).save(*args, **kwargs)

        self.esi_sso_url = EsiSecurity(
            client_id=self.esi_client_id,
            redirect_uri=self.esi_callback_url,
            secret_key=self.esi_secret_key,
            headers={'User-Agent': "Krypted Platform"}
        ).get_auth_uri(scopes=",".join(
            self.esi_scope.name for self.esi_scope in self.esi_scopes.all()).split(","), state=self.esi_client_id)

        super(EveClient, self).save(*args, **kwargs)

    def __str__(self):
        return self.esi_callback_url

    @staticmethod
    def get_eve_client():
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
        if 'esi_app' in cache:
            return cache.get('esi_app')
        else:
            esi_app = EsiApp(cache_time=86400).get_latest_swagger
            cache.set('esi_app', esi_app, timeout=86400)
            return esi_app

    @staticmethod
    def get_esi_client(token=None):
        return EsiClient(security=EveClient.get_esi_security(), headers={'User-Agent': "Krypted Platform"})

    @staticmethod
    def get_esi_security(token=None):
        client = EveClient.get_eve_client()
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
    character = models.OneToOneField(
        "EveCharacter", on_delete=models.CASCADE, related_name="eve_token")
    user = models.ForeignKey(User, null=True, on_delete=models.CASCADE)

    def __str__(self):
        return "<%s:%s>" % (self.character, self.user)

    @staticmethod
    def format_scopes(scopes):
        if type(scopes) is str:
            return scopes.split(",")
        else:
            return ",".join(scopes)

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
    portrait = models.URLField(max_length=255, blank=True, null=True)
    external_id = models.IntegerField(unique=True)

    def __str__(self):
        return self.name


class EveCharacter(EveEntity):
    corporation = models.ForeignKey(
        "EveCorporation", null=True, on_delete=models.SET_NULL)

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
        self.portrait = "https://imageserver.eveonline.com/Corporation/%s_64.png" % self.external_id
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
        self.portrait = "https://imageserver.eveonline.com/Alliance/%s_32.png" % self.external_id
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


"""
Data Models
These models represent EVE Online data for their representative entities.
"""


class EveWalletTransaction(models.Model):
    client_id = models.IntegerField()
    date = models.DateTimeField()
    is_buy = models.BooleanField()
    is_personal = models.BooleanField()
    journal_ref_id = models.IntegerField()
    location_id = models.IntegerField()
    quantity = models.IntegerField()
    transcation_id = models.IntegerField()
    type_id = models.IntegerField()
    type_name = models.CharField(max_length=32)
    unit_price = models.FloatField()
    entity = models.ForeignKey("EveEntity", on_delete=models.CASCADE)
