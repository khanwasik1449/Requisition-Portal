from django.db import models

class Contract(models.Model):
    date = models.DateField(auto_now_add=True)

    pin = models.CharField(max_length=50)
    name = models.CharField(max_length=200)

    designation = models.CharField(max_length=200)
    new_designation = models.CharField(max_length=200, blank=True, null=True)

    start_date = models.DateField(default='2000-01-01')
    end_date = models.DateField(default='2000-01-01')

    salary = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    contract_type = models.CharField(max_length=50, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.pin} - {self.name}"


class EmailLog(models.Model):
    contract = models.ForeignKey(Contract, on_delete=models.SET_NULL, null=True, blank=True)
    recipient_email = models.EmailField()
    recipient_name = models.CharField(max_length=200, blank=True, default='')
    subject = models.CharField(max_length=500)
    status = models.CharField(max_length=20)  # sent / failed
    error_message = models.TextField(blank=True, default='')
    batch_id = models.CharField(max_length=100, blank=True, default='')
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-sent_at']

    def __str__(self):
        return f"{self.recipient_email} - {self.status} - {self.sent_at}"


class EmailConfig(models.Model):
    email_host = models.CharField(max_length=200, default='smtp.gmail.com')
    email_port = models.IntegerField(default=587)
    email_use_tls = models.BooleanField(default=True)
    email_host_user = models.EmailField()
    email_host_password = models.CharField(max_length=500)
    default_from_email = models.CharField(max_length=500, default='')

    class Meta:
        verbose_name = 'Email Configuration'
        verbose_name_plural = 'Email Configuration'

    def __str__(self):
        return self.email_host_user

    @classmethod
    def get_config(cls):
        config = cls.objects.first()
        if not config:
            config = cls(
                email_host='smtp.gmail.com',
                email_port=587,
                email_use_tls=True,
                email_host_user='',
                email_host_password='',
                default_from_email='',
            )
            config.save()
        return config
