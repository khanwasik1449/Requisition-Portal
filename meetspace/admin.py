from django.contrib import admin

from .models import Announcement, Booking, Room


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ('room_number', 'floor', 'min_occupancy', 'max_occupancy', 'is_active')
    list_filter = ('is_active', 'floor')
    list_editable = ('is_active',)
    search_fields = ('room_number', 'floor')
    ordering = ('room_number',)


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('meeting_title', 'room', 'user', 'date', 'start_time', 'end_time', 'status')
    list_filter = ('status', 'date')
    search_fields = ('meeting_title', 'user__email', 'room__room_number')
    date_hierarchy = 'date'


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ('message', 'created_by', 'created_at')
    search_fields = ('message',)
