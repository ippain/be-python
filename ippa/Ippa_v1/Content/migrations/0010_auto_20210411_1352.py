# -*- coding: utf-8 -*-
# Generated by Django 1.11.22 on 2021-04-11 13:52
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('Content', '0009_article_articlegroup'),
    ]

    operations = [
        migrations.AddField(
            model_name='article',
            name='doc_type',
            field=models.CharField(choices=[('news', 'News'), ('article', 'Article')], default='news', max_length=255),
        ),
        migrations.AlterField(
            model_name='articlegroup',
            name='article',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='groups', to='Content.Article'),
        ),
    ]
