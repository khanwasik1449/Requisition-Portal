from django.db import models
from decimal import Decimal


class Payslip(models.Model):
    pin = models.CharField(max_length=50)
    name = models.CharField(max_length=200)
    designation = models.CharField(max_length=200)
    gender = models.CharField(max_length=20, blank=True, null=True)
    tin = models.CharField(max_length=50, blank=True, null=True)
    month = models.CharField(max_length=20)
    year = models.CharField(max_length=4)
    project = models.CharField(max_length=200, default="BUIED")
    branch = models.CharField(max_length=200, default="Niketon Housing, Gulshan")

    basic_salary = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    house_rent = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    medical_allowance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    conveyance = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    festival_bonus = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    arrears = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    others = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    transport = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    income_tax = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    other_deduction = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    def total_salary(self):
        return self.basic_salary

    def total_allowance(self):
        return self.house_rent + self.medical_allowance + self.conveyance

    def gross_salary(self):
        return self.basic_salary + self.total_allowance()

    def total_deduction(self):
        return self.transport + self.income_tax + self.other_deduction

    def net_salary(self):
        return self.gross_salary() - self.total_deduction()

    def __str__(self):
        return f"{self.pin} - {self.month}/{self.year}"


class PayslipRequest(models.Model):
    name = models.CharField(max_length=200)
    pin = models.CharField(max_length=50)
    months = models.CharField(max_length=200, help_text="e.g. January, February")
    year = models.CharField(max_length=4, default="2026")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.pin}) - {self.months}"