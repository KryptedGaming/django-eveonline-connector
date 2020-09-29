# Generated by Django 2.2.13 on 2020-09-20 22:05

from django.db import migrations

def load_required_migrations(apps, schema_editor):
    EveScope = apps.get_model('django_eveonline_connector', 'EveScope')
    required_scopes = ['publicData', 'esi-contracts.read_character_contracts.v1', 'esi-mail.read_mail.v1', 'esi-skills.read_skills.v1', 'esi-skills.read_skillqueue.v1', 'esi-wallet.read_character_wallet.v1', 'esi-characters.read_contacts.v1',
                       'esi-corporations.read_corporation_membership.v1', 'esi-assets.read_assets.v1', 'esi-clones.read_clones.v1', 'esi-markets.read_character_orders.v1', 'esi-characters.read_corporation_roles.v1', 'esi-universe.read_structures.v1', 'esi-characters.read_standings.v1']
    EveScope.objects.all().delete()
    for scope in required_scopes:
        if EveScope.objects.filter(name=scope).exists():
            EveScope.objects.update(name=scope, required=True)
        else:
            EveScope.objects.create(name=scope, required=True)

def unload_required_migrations(apps, schema_editor):
    EveScope = apps.get_model('django_eveonline_connector', 'EveScope')
    EveScope.objects.all().delete() # dangerous but it'll be fine 

class Migration(migrations.Migration):

    dependencies = [
        ('django_eveonline_connector', '0028_auto_20200920_2202'),
    ]

    operations = [
        migrations.RunPython(load_required_migrations, reverse_code=unload_required_migrations)
    ]
