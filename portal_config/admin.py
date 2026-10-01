from django.contrib import admin

from .models import FormField, Module, WorkflowStage


class FormFieldInline(admin.TabularInline):
    model = FormField
    extra = 0
    fields = (
        'key', 'label', 'field_type', 'required', 'is_system',
        'visible_to_requester', 'step', 'order',
    )
    ordering = ('step', 'order', 'id')


class WorkflowStageInline(admin.TabularInline):
    model = WorkflowStage
    extra = 0
    fields = ('key', 'name', 'order', 'approver_role', 'actions', 'is_terminal', 'is_active')
    ordering = ('order', 'id')


@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    list_display = ('name', 'key', 'is_active', 'order', 'field_count', 'stage_count')
    list_editable = ('is_active', 'order')
    search_fields = ('name', 'key')

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('fields', 'stages')

    @admin.display(description='Fields')
    def field_count(self, obj):
        return obj.fields.count()

    @admin.display(description='Stages')
    def stage_count(self, obj):
        return obj.stages.count()


@admin.register(FormField)
class FormFieldAdmin(admin.ModelAdmin):
    list_display = ('key', 'label', 'module', 'field_type', 'required', 'is_system', 'step', 'order')
    list_filter = ('module', 'field_type', 'required', 'is_system')
    list_editable = ('required', 'is_system', 'step', 'order')
    search_fields = ('key', 'label')
    ordering = ('module', 'step', 'order')


@admin.register(WorkflowStage)
class WorkflowStageAdmin(admin.ModelAdmin):
    list_display = ('name', 'key', 'module', 'order', 'approver_role', 'actions', 'is_terminal', 'is_active')
    list_filter = ('module', 'is_active', 'is_terminal')
    list_editable = ('order', 'approver_role', 'actions', 'is_terminal', 'is_active')
    search_fields = ('key', 'name')
    ordering = ('module', 'order')
    filter_horizontal = ('amendable_fields',)