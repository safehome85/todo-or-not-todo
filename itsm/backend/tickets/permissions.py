from rest_framework import permissions
from users.models import User

class IsITStaff(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role in [User.Role.IT_SPECIALIST, User.Role.IT_ADMIN])

class IsClient(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role in [User.Role.CLIENT_USER, User.Role.CLIENT_ADMIN])
