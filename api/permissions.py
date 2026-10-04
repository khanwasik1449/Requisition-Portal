from rest_framework import permissions
from accounts.models import User


class IsAdminUser(permissions.BasePermission):
    """Allow only admin users."""
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_admin()


class IsSupervisor(permissions.BasePermission):
    """Allow supervisor, grants, transport_admin, ict_admin, internal_admin, hr_admin, admin."""
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.is_supervisor() or request.user.is_admin()


class IsGrants(permissions.BasePermission):
    """Allow grants, admin."""
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.is_grants() or request.user.is_admin()


class IsTransportAdmin(permissions.BasePermission):
    """Allow transport_admin, admin."""
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.is_transport_admin() or request.user.is_admin()


class IsICTAdmin(permissions.BasePermission):
    """Allow ict_admin, admin."""
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.is_ict_admin() or request.user.is_admin()


class IsInternalAdmin(permissions.BasePermission):
    """Allow internal_admin, admin."""
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.is_internal_admin() or request.user.is_admin()


class IsHRAdmin(permissions.BasePermission):
    """Allow hr_admin, admin."""
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.is_hr_admin() or request.user.is_admin()


class IsRequester(permissions.BasePermission):
    """Allow any authenticated user (requester role)."""
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated


class IsOwnerOrAdmin(permissions.BasePermission):
    """Allow object owner or admin."""
    def has_object_permission(self, request, view, obj):
        if request.user.is_admin():
            return True
        # Check if object has user field
        if hasattr(obj, 'user'):
            return obj.user == request.user
        # For bookings, check email
        if hasattr(obj, 'email'):
            return obj.email.lower() == request.user.email.lower()
        return False


class ReadOnly(permissions.BasePermission):
    """Allow only safe methods."""
    def has_permission(self, request, view):
        return request.method in permissions.SAFE_METHODS