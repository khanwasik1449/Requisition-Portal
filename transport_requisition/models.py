from django.db import models
from django.conf import settings
from django.utils import timezone


class Driver(models.Model):
    name = models.CharField(max_length=200)
    pin = models.CharField(max_length=50)
    joining_date = models.DateField()
    education = models.CharField(max_length=100)
    cell_number = models.CharField(max_length=50)
    car_no = models.CharField(max_length=100)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.car_no})"


class TransportRequisition(models.Model):
    class Status(models.TextChoices):
        PENDING_FIRST = 'pending_first', 'Pending First Approval'
        PENDING_SECOND = 'pending_second', 'Pending Second Approval'
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected'

    class VehicleType(models.TextChoices):
        SEDAN = 'sedan', 'Sedan Car (3 Users)'
        NOAH = 'noah', 'Micro Noah (7 Users)'
        HIACE_11 = 'hiace_11', 'Micro Hi-Ace (11 Users)'
        HIACE_14 = 'hiace_14', 'Micro Hi-Ace (14 Users)'
        DELIVERY_VAN = 'delivery_van', 'Delivery Van (Covered Van, Pickup etc.)'
        OTHER = 'other', 'Other'

    request_number = models.CharField(max_length=30, unique=True, blank=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True, related_name='transport_requisitions')
    full_name = models.CharField(max_length=200)
    email_address = models.EmailField()
    mobile_number = models.CharField(max_length=50)
    designation = models.CharField(max_length=200)
    pin = models.CharField(max_length=100)
    num_passengers = models.PositiveIntegerField(default=1)
    vehicle_type = models.CharField(max_length=20, choices=VehicleType.choices, default=VehicleType.SEDAN)
    vehicle_type_other = models.CharField(max_length=200, blank=True)
    pick_up_date = models.DateField()
    pick_up_time = models.TimeField()
    pick_up_location = models.CharField(max_length=300)
    destination = models.CharField(max_length=300)
    drop_off_date = models.DateField()
    drop_off_time = models.TimeField()
    drop_off_location = models.CharField(max_length=300)
    travelling_reason = models.TextField()
    project_name_code = models.CharField(max_length=300)
    budget_code = models.CharField(max_length=300)
    supervisor_acknowledged = models.BooleanField(default=False)
    comments_remarks = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING_FIRST)
    first_approver = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='transport_first_approvals')
    second_approver = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='transport_second_approvals')
    first_approved_at = models.DateTimeField(null=True, blank=True)
    second_approved_at = models.DateTimeField(null=True, blank=True)
    rejected_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    driver = models.ForeignKey(Driver, on_delete=models.SET_NULL, null=True, blank=True, related_name='assignments')
    assigned_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='transport_assignments')
    assigned_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.request_number:
            year = timezone.now().year
            prefix = 'TRP'
            last = TransportRequisition.objects.filter(request_number__startswith=f'{prefix}-{year}-').count()
            self.request_number = f'{prefix}-{year}-{last + 1:04d}'
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.request_number} — {self.destination} by {self.full_name}"
