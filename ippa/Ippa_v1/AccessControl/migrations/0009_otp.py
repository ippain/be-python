# -*- coding: utf-8 -*-
# Generated by Django 1.11.22 on 2020-05-28 18:48
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('AccessControl', '0008_auto_20200430_0516'),
    ]

    operations = [
        migrations.CreateModel(
            name='OTP',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_on', models.DateTimeField(auto_now_add=True)),
                ('updated_on', models.DateTimeField(auto_now=True)),
                ('is_deleted', models.SmallIntegerField(default=0)),
                ('otp', models.CharField(blank=True, max_length=6, null=True)),
                ('is_valid', models.BooleanField(default=True)),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='AccessControl.IppaUser')),
            ],
            options={
                'abstract': False,
            },
        ),
    ]
