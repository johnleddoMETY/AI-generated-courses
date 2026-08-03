from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0002_course'),
    ]

    operations = [
        migrations.AddField(
            model_name='syllabus',
            name='owner_id',
            # Default backfills any pre-ownership dev rows; new rows always
            # set this explicitly in courses/views.py.
            field=models.CharField(default='', max_length=36),
            preserve_default=False,
        ),
    ]
