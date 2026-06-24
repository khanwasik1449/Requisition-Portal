from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import Contract


@admin.register(Contract)
class ContractAdmin(admin.ModelAdmin):
    list_display = (
        'pin',
        'name',
        'designation',
        'new_designation',
        'contract_type',
        'start_date',
        'end_date',
        'salary',
        'pdf_link'
    )

    search_fields = ('pin', 'name', 'designation')
    list_filter = ('contract_type', 'designation')

    def pdf_link(self, obj):
        url = reverse('generate_pdf', args=[obj.id])
        return format_html('<a href="{}" target="_blank">Download PDF</a>', url)

    pdf_link.short_description = "PDF"
