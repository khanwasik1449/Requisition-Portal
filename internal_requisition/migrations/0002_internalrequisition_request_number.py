from django.db import migrations, models
from django.utils import timezone


def gen_request_number(apps, schema_editor):
    InternalRequisition = apps.get_model('internal_requisition', 'InternalRequisition')
    for i, obj in enumerate(InternalRequisition.objects.all().order_by('id')):
        year = timezone.now().year
        obj.request_number = f'INT-{year}-{i + 1:04d}'
        obj.save(update_fields=['request_number'])


class Migration(migrations.Migration):

    dependencies = [
        ('internal_requisition', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='internalrequisition',
            name='request_number',
            field=models.CharField(blank=True, max_length=30, null=True),
        ),
        migrations.RunPython(gen_request_number, reverse_code=migrations.RunPython.noop),
        migrations.AlterField(
            model_name='internalrequisition',
            name='request_number',
            field=models.CharField(blank=True, max_length=30, unique=True),
        ),
    ]
