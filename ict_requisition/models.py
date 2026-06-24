from django.db import models
from django.conf import settings
from django.utils import timezone


class ICTRequisition(models.Model):
    class Status(models.TextChoices):
        PENDING_FIRST = 'pending_first', 'Pending First Approval'
        PENDING_SECOND = 'pending_second', 'Pending Second Approval'
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected'

    request_number = models.CharField(max_length=30, unique=True, blank=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True, related_name='ict_requisitions')
    full_name = models.CharField(max_length=200)
    email_address = models.EmailField()
    designation = models.CharField(max_length=200)
    pin_number = models.CharField(max_length=100)
    contact_number = models.CharField(max_length=50)
    device_equipment = models.TextField()
    equipment_specification = models.TextField(blank=True)
    purpose = models.TextField()
    requisition_date = models.DateField()
    requirement_date = models.DateField()
    return_date = models.DateField(null=True, blank=True)
    supervisor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='ict_supervisor_for')
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING_FIRST)
    first_approver = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='ict_first_approvals')
    second_approver = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='ict_second_approvals')
    first_approved_at = models.DateTimeField(null=True, blank=True)
    second_approved_at = models.DateTimeField(null=True, blank=True)
    rejected_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def equipment_list(self):
        return [e for e in self.device_equipment.split('\n') if e]

    def equipment_count(self):
        return len(self.equipment_list())

    def equipment_first(self):
        items = self.equipment_list()
        return items[0] if items else ''

    def save(self, *args, **kwargs):
        if not self.request_number:
            year = timezone.now().year
            prefix = 'ICT'
            last = ICTRequisition.objects.filter(request_number__startswith=f'{prefix}-{year}-').count()
            self.request_number = f'{prefix}-{year}-{last + 1:04d}'
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.request_number} — {self.equipment_first()} by {self.full_name}"
