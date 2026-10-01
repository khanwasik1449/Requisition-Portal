from django.urls import path

from . import views

app_name = 'meetspace'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),

    # Rooms
    path('rooms/', views.room_list, name='room_list'),
    path('rooms/new/', views.room_create, name='room_create'),
    path('rooms/<int:pk>/edit/', views.room_edit, name='room_edit'),
    path('rooms/<int:pk>/toggle/', views.room_toggle, name='room_toggle'),

    # Bookings
    path('bookings/', views.booking_list, name='booking_list'),
    path('bookings/new/', views.booking_create, name='booking_create'),
    path('bookings/<int:pk>/', views.booking_detail, name='booking_detail'),
    path('track/', views.track_view, name='track'),
    path('bookings/<int:pk>/approve/', views.booking_approve, name='booking_approve'),
    path('bookings/<int:pk>/reject/', views.booking_reject, name='booking_reject'),
    path('bookings/<int:pk>/cancel/', views.booking_cancel, name='booking_cancel'),
    path('bookings/<int:pk>/suggest-alternatives/', views.booking_suggest_alternatives,
         name='booking_suggest_alternatives'),
    path('bookings/<int:pk>/accept-alternative/', views.booking_accept_alternative,
         name='booking_accept_alternative'),
    path('bookings/<int:pk>/reject-alternatives/', views.booking_reject_alternatives,
         name='booking_reject_alternatives'),

    # Availability search
    path('availability/', views.availability, name='availability'),

    # Announcements
    path('announcements/new/', views.announcement_create, name='announcement_create'),
    path('announcements/<int:pk>/delete/', views.announcement_delete, name='announcement_delete'),
]
