from django.db import models


class Employee(models.Model):
    pin = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=200)
    designation = models.CharField(max_length=200)
    gender = models.CharField(max_length=20, blank=True, null=True)
    tin = models.CharField(max_length=50, blank=True, null=True)
    phone = models.CharField(max_length=15, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    salary = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    project = models.CharField(max_length=200, default="BUIED")
    branch = models.CharField(max_length=200, default="Niketon Housing, Gulshan")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.pin} - {self.name}"


class EmployeeSalary(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    month = models.CharField(max_length=20)
    year = models.CharField(max_length=4)
    total_salary = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['employee', 'month', 'year']

    def basic(self):
        return self.total_salary * 50 / 100
    
    def house_rent(self):
        return self.total_salary * 30 / 100
    
    def medical(self):
        return self.total_salary * 10 / 100
    
    def conveyance(self):
        return self.total_salary * 10 / 100