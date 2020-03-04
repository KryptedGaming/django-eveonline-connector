# Generated by Django 2.2.10 on 2020-02-27 23:43

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('django_eveonline_connector', '0020_auto_20200227_2151'),
    ]

    operations = [
        migrations.AlterField(
            model_name='eveasset',
            name='entity',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='django_eveonline_connector.EveEntity'),
        ),
        migrations.CreateModel(
            name='EveClone',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('location_id', models.IntegerField()),
                ('location_type', models.CharField(max_length=64)),
                ('jump_clone_id', models.IntegerField()),
                ('location', models.CharField(max_length=128)),
                ('implants', models.TextField()),
                ('entity', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='django_eveonline_connector.EveEntity')),
            ],
            options={
                'abstract': False,
            },
        ),
    ]
