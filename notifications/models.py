from django.db import models
from django.conf import settings


class Department(models.TextChoices):
    ICT = 'ict', 'ICT'
    TRANSPORT = 'transport', 'Transport'
    INTERNAL = 'internal', 'Internal'


class EmailConfig(models.Model):
    department = models.CharField(max_length=20, choices=Department.choices, unique=True)
    email_host = models.CharField(max_length=300, default='smtp.gmail.com')
    email_port = models.PositiveIntegerField(default=587)
    email_host_user = models.CharField(max_length=300)
    email_host_password = models.CharField(max_length=300)
    email_use_tls = models.BooleanField(default=True)
    from_email = models.EmailField(help_text='Sender address for this department')
    notification_email = models.EmailField(help_text='Department inbox that receives notifications')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Email Configuration'

    def __str__(self):
        return f'{self.get_department_display()} — {self.from_email}'


class EmailLog(models.Model):
    class Status(models.TextChoices):
        SUCCESS = 'success', 'Sent'
        FAILED = 'failed', 'Failed'

    department = models.CharField(max_length=20, choices=Department.choices)
    email_type = models.CharField(max_length=30, choices=[
        ('approval_request', 'Approval Request'),
        ('notification', 'Status Notification'),
    ])
    req_type = models.CharField(max_length=20, blank=True)
    req_id = models.PositiveIntegerField(null=True, blank=True)
    recipient = models.EmailField()
    subject = models.CharField(max_length=300)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.FAILED)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.get_department_display()} {self.get_email_type_display()} — {self.status}'


class AuditLog(models.Model):
    class Action(models.TextChoices):
        CREATED = 'created', 'Created'
        PENDING_FIRST = 'pending_first', 'Pending First Approval'
        PENDING_SECOND = 'pending_second', 'Pending Second Approval'
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected'

    req_type = models.CharField(max_length=20, choices=Department.choices)
    req_id = models.PositiveIntegerField()
    request_number = models.CharField(max_length=30, blank=True)
    action = models.CharField(max_length=20, choices=Action.choices)
    performed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    details = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Audit Log'
        verbose_name_plural = 'Audit Logs'

    def __str__(self):
        return f'{self.get_req_type_display()} #{self.request_number} — {self.get_action_display()}'
