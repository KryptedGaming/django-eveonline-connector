# Generated by Django 2.2.13 on 2020-10-04 00:46

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('django_eveonline_connector', '0033_auto_20200930_1805'),
    ]

    operations = [
        migrations.CreateModel(
            name='EveStructure',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('corporation_id', models.BigIntegerField()),
                ('fuel_expires', models.DateTimeField(null=True)),
                ('next_reinforce_apply', models.DateTimeField(null=True)),
                ('next_reinforce_hour', models.BigIntegerField(null=True)),
                ('next_reinforce_weekday', models.BigIntegerField(null=True)),
                ('profile_id', models.BigIntegerField()),
                ('reinforce_hour', models.BigIntegerField()),
                ('reinforce_weekday', models.BigIntegerField(null=True)),
                ('services', models.TextField(null=True)),
                ('state', models.CharField(max_length=64)),
                ('state_timer_end', models.DateTimeField(null=True)),
                ('state_timer_start', models.DateTimeField(null=True)),
                ('structure_id', models.BigIntegerField()),
                ('system_id', models.BigIntegerField()),
                ('unanchors_at', models.DateTimeField(null=True)),
                ('owner_id', models.BigIntegerField()),
                ('solar_system_id', models.BigIntegerField()),
                ('type_id', models.BigIntegerField(null=True)),
                ('name', models.CharField(max_length=256)),
                ('entity', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='django_eveonline_connector.EveEntity')),
            ],
            options={
                'abstract': False,
            },
        ),
    ]
