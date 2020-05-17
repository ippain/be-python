# -*- coding: utf-8 -*-
# Generated by Django 1.11.22 on 2020-05-17 18:41
from __future__ import unicode_literals

import django.contrib.postgres.fields.jsonb
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Content', '0004_ad'),
    ]

    operations = [
        migrations.CreateModel(
            name='Promotions',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_on', models.DateTimeField(auto_now_add=True)),
                ('updated_on', models.DateTimeField(auto_now=True)),
                ('is_deleted', models.SmallIntegerField(default=0)),
                ('tournament_title', models.TextField(blank=True, null=True)),
                ('tournament_file_url', models.TextField(blank=True, null=True)),
                ('htgt', django.contrib.postgres.fields.jsonb.JSONField(blank=True, default={}, help_text='How to get Tagged', null=True)),
                ('network_logo', models.TextField(blank=True, null=True)),
                ('cover_img', models.TextField(blank=True, null=True)),
                ('term_and_con', models.TextField(blank=True, null=True)),
                ('network_name', models.CharField(blank=True, max_length=255, null=True)),
                ('introduction', django.contrib.postgres.fields.jsonb.JSONField(blank=True, default={}, null=True)),
                ('pokergenie_carousal', django.contrib.postgres.fields.jsonb.JSONField(blank=True, default=[], null=True)),
                ('deposit_bonus', django.contrib.postgres.fields.jsonb.JSONField(blank=True, default={b'benefits': [], b'code': b'', b'note_str': b''}, null=True)),
                ('free_entry_trn', django.contrib.postgres.fields.jsonb.JSONField(blank=True, default=[], null=True)),
                ('status', models.CharField(choices=[('Pending', 'Pending'), ('Preview', 'Preview'), ('Live', 'Live')], default='Pending', max_length=255)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Tournaments',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_on', models.DateTimeField(auto_now_add=True)),
                ('updated_on', models.DateTimeField(auto_now=True)),
                ('is_deleted', models.SmallIntegerField(default=0)),
                ('tournament_date', models.DateTimeField(blank=True, null=True)),
                ('event_name', models.CharField(blank=True, max_length=255, null=True)),
                ('buy_in', models.CharField(blank=True, max_length=255, null=True)),
                ('guaranteed', models.CharField(blank=True, max_length=255, null=True)),
                ('network_name', models.CharField(blank=True, max_length=255, null=True)),
            ],
            options={
                'abstract': False,
            },
        ),
    ]
