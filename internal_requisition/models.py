from django.db import models
from django.conf import settings
from django.utils import timezone


class InternalEquipmentItem(models.Model):
    requisition = models.ForeignKey('InternalRequisition', on_delete=models.CASCADE, related_name='equipment_items')
    name = models.CharField(max_length=300)
    quantity = models.PositiveIntegerField(default=1)
    purpose = models.TextField()

    def __str__(self):
        return f"{self.name} x{self.quantity}"


class InternalRequisition(models.Model):
    class Status(models.TextChoices):
        PENDING_FIRST = 'pending_first', 'Pending First Approval'
        PENDING_SECOND = 'pending_second', 'Pending Second Approval'
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected'

    request_number = models.CharField(max_length=30, unique=True, blank=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True, related_name='internal_requisitions')
    full_name = models.CharField(max_length=200)
    email_address = models.EmailField()
    mobile_number = models.CharField(max_length=50)
    designation = models.CharField(max_length=200)
    pin = models.CharField(max_length=100)
    department = models.CharField(max_length=100)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING_FIRST)
    first_approver = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='internal_first_approvals')
    second_approver = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='internal_second_approvals')
    first_approved_at = models.DateTimeField(null=True, blank=True)
    second_approved_at = models.DateTimeField(null=True, blank=True)
    rejected_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.request_number:
            year = timezone.now().year
            prefix = 'INT'
            last = InternalRequisition.objects.filter(request_number__startswith=f'{prefix}-{year}-').count()
            self.request_number = f'{prefix}-{year}-{last + 1:04d}'
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.request_number} — {self.full_name}"
