from django.urls import path

from . import views

app_name = 'portal_config'

urlpatterns = [
    path('', views.module_list, name='module_list'),
    path('<slug:module_key>/toggle/', views.module_toggle, name='module_toggle'),
    path('<slug:module_key>/fields/', views.field_list, name='field_list'),
    path('<slug:module_key>/fields/new/', views.field_edit, name='field_create'),
    path('<slug:module_key>/fields/<int:pk>/edit/', views.field_edit, name='field_edit'),
    path('<slug:module_key>/fields/<int:pk>/delete/', views.field_delete, name='field_delete'),
    path('<slug:module_key>/workflow/', views.workflow, name='workflow'),
    path('<slug:module_key>/workflow/add-stage/', views.workflow_add_stage, name='workflow_add_stage'),
]