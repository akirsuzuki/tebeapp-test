# Generated by Django 2.0.5 on 2019-04-04 22:15

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('vanapp', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Pref',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('pref', models.CharField(max_length=6, verbose_name='都道府県')),
                ('name', models.CharField(max_length=10)),
            ],
        ),
    ]
