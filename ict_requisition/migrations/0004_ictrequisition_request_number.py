from django.db import migrations, models
from django.utils import timezone


def gen_request_number(apps, schema_editor):
    ICTRequisition = apps.get_model('ict_requisition', 'ICTRequisition')
    for i, obj in enumerate(ICTRequisition.objects.all().order_by('id')):
        year = timezone.now().year
        obj.request_number = f'ICT-{year}-{i + 1:04d}'
        obj.save(update_fields=['request_number'])


class Migration(migrations.Migration):

    dependencies = [
        ('ict_requisition', '0003_multi_equipment'),
    ]

    operations = [
        migrations.AddField(
            model_name='ictrequisition',
            name='request_number',
            field=models.CharField(blank=True, max_length=30, null=True),
        ),
        migrations.RunPython(gen_request_number, reverse_code=migrations.RunPython.noop),
        migrations.AlterField(
            model_name='ictrequisition',
            name='request_number',
            field=models.CharField(blank=True, max_length=30, unique=True),
        ),
    ]
