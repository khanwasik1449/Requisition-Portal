from django.contrib import admin

from .models import Driver, TransportRequisition, Vehicle


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    """Fleet list the transport admin allocates from.

    Only vehicles marked ``available`` are offered on the assignment screen, so
    retiring or sending one to maintenance here takes it out of circulation
    without touching any requisition.
    """

    list_display = ('registration_number', 'vehicle_type', 'make_model', 'capacity', 'status')
    list_filter = ('status', 'vehicle_type')
    list_editable = ('status',)
    search_fields = ('registration_number', 'make_model')
    ordering = ('registration_number',)


@admin.register(Driver)
class DriverAdmin(admin.ModelAdmin):
    list_display = ('name', 'car_no', 'cell_number', 'pin')
    search_fields = ('name', 'car_no', 'cell_number', 'pin')
    ordering = ('name',)


@admin.register(TransportRequisition)
class TransportRequisitionAdmin(admin.ModelAdmin):
    list_display = ('request_number', 'full_name', 'destination', 'status', 'created_at')
    list_filter = ('status', 'vehicle_type')
    search_fields = ('request_number', 'full_name', 'email_address', 'destination',
                     'project_name_code', 'budget_code')
    readonly_fields = ('request_number',)
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Request', {'fields': ('request_number', 'user', 'status')}),
        ('Requester', {'fields': ('full_name', 'email_address', 'mobile_number',
                                  'designation', 'pin', 'num_passengers')}),
        ('Trip', {'fields': ('vehicle_type', 'vehicle_type_other', 'pick_up_date',
                             'pick_up_time', 'pick_up_location', 'destination',
                             'drop_off_date', 'drop_off_time', 'drop_off_location',
                             'travelling_reason')}),
        ('Funding', {'fields': ('project_name_code', 'budget_code')}),
        ('Approval', {'fields': ('first_approver', 'first_approved_at',
                                 'grants_approver', 'grants_approved_at',
                                 'grants_amended', 'grants_remarks',
                                 'transport_approver', 'transport_approved_at',
                                 'rejected_at', 'rejection_reason')}),
        ('Assignment', {'fields': ('vehicle', 'driver', 'assigned_by', 'assigned_at')}),
        ('Other', {'fields': ('supervisor_acknowledged', 'comments_remarks', 'extra_data')}),
    )