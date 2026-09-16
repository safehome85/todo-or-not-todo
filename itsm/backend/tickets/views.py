from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.utils import timezone
from .models import Ticket, TicketCategory, SLA, TicketComment, TicketRating
from .serializers import (
    TicketSerializer, TicketCategorySerializer, SLASerializer,
    TicketCommentSerializer, TicketRatingSerializer
)
from users.models import User
from .permissions import IsITStaff, IsClient

class SLAViewSet(viewsets.ModelViewSet):
    queryset = SLA.objects.all()
    serializer_class = SLASerializer
    permission_classes = [IsITStaff]

class TicketCategoryViewSet(viewsets.ModelViewSet):
    queryset = TicketCategory.objects.all()
    serializer_class = TicketCategorySerializer

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
             permission_classes = [IsITStaff]
        else:
             permission_classes = [permissions.IsAuthenticated]
        return [permission() for permission in permission_classes]

class TicketViewSet(viewsets.ModelViewSet):
    serializer_class = TicketSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role in [User.Role.IT_ADMIN, User.Role.IT_SPECIALIST]:
            return Ticket.objects.all()
        elif user.role == User.Role.CLIENT_ADMIN:
            return Ticket.objects.filter(company=user.company)
        else:
            return Ticket.objects.filter(creator=user)

    def perform_create(self, serializer):
        # A ticket must belong to the user's company
        if not self.request.user.company:
            from rest_framework.exceptions import ValidationError
            raise ValidationError("You must belong to a company to create a ticket.")
        serializer.save(creator=self.request.user, company=self.request.user.company)

    def perform_update(self, serializer):
        user = self.request.user
        if user.role in [User.Role.CLIENT_USER, User.Role.CLIENT_ADMIN]:
            # Clients cannot change priority, status, assignee, or company directly via PUT/PATCH
            restricted_fields = ['priority', 'status', 'assignee', 'company', 'category']
            for field in restricted_fields:
                 if field in self.request.data:
                      from rest_framework.exceptions import PermissionDenied
                      raise PermissionDenied(f"Clients are not allowed to update the {field} field.")
        serializer.save()

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def add_comment(self, request, pk=None):
        ticket = self.get_object()
        serializer = TicketCommentSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(ticket=ticket, author=request.user)
            # Logic for first response time could go here, or in signals
            if request.user.role in [User.Role.IT_SPECIALIST, User.Role.IT_ADMIN]:
                 if not ticket.first_response_at:
                     ticket.first_response_at = timezone.now()
                     if ticket.status == Ticket.Status.OPEN:
                         ticket.status = Ticket.Status.IN_PROGRESS
                     ticket.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], permission_classes=[IsITStaff])
    def change_status(self, request, pk=None):
        ticket = self.get_object()
        new_status = request.data.get('status')
        if new_status not in [choice[0] for choice in Ticket.Status.choices]:
            return Response({'error': 'Invalid status'}, status=status.HTTP_400_BAD_REQUEST)

        ticket.status = new_status
        if new_status == Ticket.Status.RESOLVED and not ticket.resolved_at:
             ticket.resolved_at = timezone.now()
        ticket.save()
        return Response({'status': 'Status updated', 'ticket_id': ticket.id, 'new_status': ticket.status})

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def reopen(self, request, pk=None):
        ticket = self.get_object()
        if request.user.role not in [User.Role.CLIENT_USER, User.Role.CLIENT_ADMIN]:
             return Response({'error': 'Only clients can reopen tickets'}, status=status.HTTP_403_FORBIDDEN)

        if ticket.status == Ticket.Status.RESOLVED:
            ticket.status = Ticket.Status.IN_PROGRESS
            ticket.resolved_at = None
            ticket.save()
            return Response({'status': 'Ticket reopened'}, status=status.HTTP_200_OK)
        return Response({'error': 'Ticket is not in a resolved state'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def rate(self, request, pk=None):
        ticket = self.get_object()

        if request.user.role not in [User.Role.CLIENT_USER, User.Role.CLIENT_ADMIN]:
            return Response({'error': 'Only clients can rate tickets'}, status=status.HTTP_403_FORBIDDEN)

        if ticket.status != Ticket.Status.RESOLVED and ticket.status != Ticket.Status.CLOSED:
             return Response({'error': 'Can only rate resolved/closed tickets'}, status=status.HTTP_400_BAD_REQUEST)

        if hasattr(ticket, 'rating'):
             return Response({'error': 'Ticket is already rated'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = TicketRatingSerializer(data=request.data)
        if serializer.is_valid():
             serializer.save(ticket=ticket, client=request.user)
             return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
