from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import Payslip


@admin.register(Payslip)
class PayslipAdmin(admin.ModelAdmin):
    list_display = ('pin', 'name', 'designation', 'month', 'year', 'basic_salary', 'gross_salary', 'net_salary', 'pdf_link')
    search_fields = ('pin', 'name', 'designation')
    list_filter = ('month', 'year')

    def pdf_link(self, obj):
        url = reverse('generate_payslip_pdf', args=[obj.id])
        return format_html('<a href="{}" target="_blank">Download PDF</a>', url)

    pdf_link.short_description = "PDF"