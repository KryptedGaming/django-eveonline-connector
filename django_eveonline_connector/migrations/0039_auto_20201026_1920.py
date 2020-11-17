# Generated by Django 2.2.13 on 2020-10-26 19:20

from django.db import migrations, models
import django.db.models.deletion


def load_required_roles(apps, schema_editor):
    EveCorporationRole = apps.get_model('django_eveonline_connector',
                                        'EveCorporationRole')
    corporation_roles = (
        ("Account_Take_1", "Account Take 1"),
        ("Account_Take_2", "Account Take 2"),
        ("Account_Take_3", "Account Take 3"),
        ("Account_Take_4", "Account Take 4"),
        ("Account_Take_5", "Account Take 5"),
        ("Account_Take_6", "Account Take 6"),
        ("Account_Take_7", "Account Take 7"),
        ("Accountant", "Accountant"),
        ("Auditor", "Auditor"),
        ("Communications_Officer", "Communications Officer"),
        ("Config_Equipment", "Config Equipment"),
        ("Config_Starbase_Equipment", "Config Starbase Equipment"),
        ("Container_Take_1", "Container Take 1"),
        ("Container_Take_2", "Container Take 2"),
        ("Container_Take_3", "Container Take 3"),
        ("Container_Take_4", "Container Take 4"),
        ("Container_Take_5", "Container Take 5"),
        ("Container_Take_6", "Container Take 6"),
        ("Container_Take_7", "Container Take 7"),
        ("Contract_Manager", "Contract Manager"),
        ("Diplomat", "Diplomat"),
        ("Director", "Director"),
        ("Factory_Manager", "Factory Manager"),
        ("Fitting_Manager", "Fitting Manager"),
        ("Hangar_Query_1", "Hangar Query 1"),
        ("Hangar_Query_2", "Hangar Query 2"),
        ("Hangar_Query_3", "Hangar Query 3"),
        ("Hangar_Query_4", "Hangar Query 4"),
        ("Hangar_Query_5", "Hangar Query 5"),
        ("Hangar_Query_6", "Hangar Query 6"),
        ("Hangar_Query_7", "Hangar Query 7"),
        ("Hangar_Take_1", "Hangar Take 1"),
        ("Hangar_Take_2", "Hangar Take 2"),
        ("Hangar_Take_3", "Hangar Take 3"),
        ("Hangar_Take_4", "Hangar Take 4"),
        ("Hangar_Take_5", "Hangar Take 5"),
        ("Hangar_Take_6", "Hangar Take 6"),
        ("Hangar_Take_7", "Hangar Take 7"),
        ("Junior_Accountant", "Junior Accountant"),
        ("Personnel_Manager", "Personnel Manager"),
        ("Rent_Factory_Facility", "Rent Factory Facility"),
        ("Rent_Office", "Rent Office"),
        ("Rent_Research_Facility", "Rent Research Facility"),
        ("Security_Officer", "Security Officer"),
        ("Starbase_Defense_Operator", "Starbase Defense Operator"),
        ("Starbase_Fuel_Technician", "Starbase Fuel Technician"),
        ("Station_Manager", "Station Manager"),
        ("Trader", "Trader"),
    )
    for role_tuple in corporation_roles:
        EveCorporationRole.objects.create(
            codename=role_tuple[0],
            name=role_tuple[1],
        )


def unload_required_roles(apps, schema_editor):
    EveCorporationRole = apps.get_model(
        'django_eveonline_connector', 'EveCorporationRole')
    EveCorporationRole.objects.all().delete()  # dangerous but it'll be fine

class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0011_update_proxy_permissions'),
        ('django_eveonline_connector', '0038_auto_20201025_1808'),
    ]

    operations = [
        migrations.CreateModel(
            name='EveCorporationRole',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('codename', models.CharField(max_length=64, unique=True)),
                ('name', models.CharField(max_length=64, unique=True)),
            ],
        ),
        migrations.CreateModel(
            name='EveGroupRule',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('include_alts', models.BooleanField(default=True)),
                ('alliances', models.ManyToManyField(blank=True, to='django_eveonline_connector.EveAlliance')),
                ('characters', models.ManyToManyField(blank=True, to='django_eveonline_connector.EveCharacter')),
                ('corporations', models.ManyToManyField(blank=True, to='django_eveonline_connector.EveCorporation')),
                ('group', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='auth.Group')),
                ('roles', models.ManyToManyField(blank=True, to='django_eveonline_connector.EveCorporationRole')),
            ],
        ),
        migrations.AddField(
            model_name='evecharacter',
            name='roles',
            field=models.ManyToManyField(blank=True, to='django_eveonline_connector.EveCorporationRole'),
        ),
        migrations.RunPython(
            load_required_roles, reverse_code=unload_required_roles
        ),
    ]