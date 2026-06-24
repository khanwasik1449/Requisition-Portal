from django.db import migrations, models
from django.utils import timezone


def gen_request_number(apps, schema_editor):
    TransportRequisition = apps.get_model('transport_requisition', 'TransportRequisition')
    for i, obj in enumerate(TransportRequisition.objects.all().order_by('id')):
        year = timezone.now().year
        obj.request_number = f'TRP-{year}-{i + 1:04d}'
        obj.save(update_fields=['request_number'])


class Migration(migrations.Migration):

    dependencies = [
        ('transport_requisition', '0002_driver_transportrequisition_assigned_at_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='transportrequisition',
            name='request_number',
            field=models.CharField(blank=True, max_length=30, null=True),
        ),
        migrations.RunPython(gen_request_number, reverse_code=migrations.RunPython.noop),
        migrations.AlterField(
            model_name='transportrequisition',
            name='request_number',
            field=models.CharField(blank=True, max_length=30, unique=True),
        ),
    ]
