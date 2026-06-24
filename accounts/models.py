from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        REQUESTER = 'requester', 'Requester'
        SUPERVISOR = 'supervisor', 'Supervisor (1st Approver)'
        ICT_APPROVER = 'ict_approver', 'ICT Approver (2nd Approver)'
        ICT_ADMIN = 'ict_admin', 'ICT Admin'
        TRANSPORT_ADMIN = 'transport_admin', 'Transport Admin'
        INTERNAL_ADMIN = 'internal_admin', 'Internal Admin'
        HR_ADMIN = 'hr_admin', 'HR Admin'
        ADMIN = 'admin', 'Admin'

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.REQUESTER)
    phone = models.CharField(max_length=15, blank=True)

    def is_approver(self):
        return self.role in [
            self.Role.SUPERVISOR, self.Role.ICT_APPROVER,
            self.Role.ICT_ADMIN, self.Role.TRANSPORT_ADMIN, self.Role.INTERNAL_ADMIN,
            self.Role.ADMIN,
        ]

    def is_first_approver(self):
        return self.role in [
            self.Role.SUPERVISOR,
            self.Role.ICT_ADMIN, self.Role.TRANSPORT_ADMIN, self.Role.INTERNAL_ADMIN,
            self.Role.ADMIN,
        ]

    def is_second_approver(self):
        return self.role in [
            self.Role.ICT_APPROVER,
            self.Role.ICT_ADMIN, self.Role.TRANSPORT_ADMIN, self.Role.INTERNAL_ADMIN,
            self.Role.ADMIN,
        ]

    def is_admin(self):
        return self.role == self.Role.ADMIN or self.is_superuser

    def is_ict_admin(self):
        return self.role in [self.Role.ICT_ADMIN, self.Role.ADMIN]

    def is_transport_admin(self):
        return self.role in [self.Role.TRANSPORT_ADMIN, self.Role.ADMIN]

    def is_internal_admin(self):
        return self.role in [self.Role.INTERNAL_ADMIN, self.Role.ADMIN]

    def is_hr_admin(self):
        return self.role in [self.Role.HR_ADMIN, self.Role.ADMIN]

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"
