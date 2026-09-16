from rest_framework import viewsets, generics, permissions, status
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from .models import Company
from .serializers import UserSerializer, CompanySerializer, RegisterSerializer
from .permissions import IsITStaff, IsClientAdmin, IsITStaffOrClientAdmin

User = get_user_model()

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = (permissions.AllowAny,)
    serializer_class = RegisterSerializer

class CompanyViewSet(viewsets.ModelViewSet):
    serializer_class = CompanySerializer

    def get_permissions(self):
        if self.action in ['create', 'destroy']:
            # Only IT Admins (or superusers) should generally create/delete companies
            # Alternatively, we allow anyone to create a company, and they become its Client Admin.
            # We'll allow authenticated users to view, but limit creation in a custom way.
            # Let's enforce ITStaff for destroy.
            if self.action == 'destroy':
                 permission_classes = [IsITStaff]
            else:
                 permission_classes = [permissions.IsAuthenticated]
        elif self.action in ['update', 'partial_update']:
            permission_classes = [IsITStaffOrClientAdmin]
        else:
            permission_classes = [permissions.IsAuthenticated]
        return [permission() for permission in permission_classes]

    def get_queryset(self):
        user = self.request.user
        if user.role in [User.Role.IT_ADMIN, User.Role.IT_SPECIALIST]:
            return Company.objects.all()
        elif user.role in [User.Role.CLIENT_ADMIN, User.Role.CLIENT_USER]:
            if user.company:
                return Company.objects.filter(id=user.company.id)
            return Company.objects.none()
        return Company.objects.none()

    def perform_update(self, serializer):
        # Client admin can only update their own company
        user = self.request.user
        if user.role == User.Role.CLIENT_ADMIN and serializer.instance != user.company:
             from rest_framework.exceptions import PermissionDenied
             raise PermissionDenied("You can only edit your own company.")
        serializer.save()

class UserViewSet(viewsets.ModelViewSet):
    serializer_class = UserSerializer

    def get_permissions(self):
        if self.action in ['create', 'destroy']:
             permission_classes = [IsITStaffOrClientAdmin]
        elif self.action in ['update', 'partial_update']:
             # Users can update themselves, or ITStaff/ClientAdmin can update others
             permission_classes = [permissions.IsAuthenticated]
        else:
             permission_classes = [permissions.IsAuthenticated]
        return [permission() for permission in permission_classes]

    def get_queryset(self):
        user = self.request.user
        if user.role in [User.Role.IT_ADMIN, User.Role.IT_SPECIALIST]:
            return User.objects.all()
        return User.objects.filter(company=user.company)

    def perform_create(self, serializer):
        user = self.request.user
        password = serializer.validated_data.pop('password', None)

        # Determine the company based on the creator's role
        if user.role == User.Role.CLIENT_ADMIN:
             instance = serializer.save(company=user.company, role=User.Role.CLIENT_USER)
        elif user.role in [User.Role.IT_ADMIN]:
             # Allow IT Admin to set roles via request data if needed, or default
             role = self.request.data.get('role', User.Role.CLIENT_USER)
             instance = serializer.save(role=role)
        else:
             instance = serializer.save(role=User.Role.CLIENT_USER)

        if password:
             instance.set_password(password)
             instance.save()

    def perform_update(self, serializer):
        # Regular users can only update themselves
        user = self.request.user
        if user.role == User.Role.CLIENT_USER and serializer.instance != user:
             from rest_framework.exceptions import PermissionDenied
             raise PermissionDenied("You can only edit your own profile.")

        # Client Admins can only update users in their company
        if user.role == User.Role.CLIENT_ADMIN and serializer.instance.company != user.company:
             from rest_framework.exceptions import PermissionDenied
             raise PermissionDenied("You can only edit users in your company.")

        serializer.save()
