from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Count, Avg, F, Q, ExpressionWrapper, DurationField
from tickets.models import Ticket, TicketRating
from users.models import User
from tickets.permissions import IsITStaff

class DashboardStatsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        # Clients can only see stats for their own company
        if user.role == User.Role.CLIENT_ADMIN:
            tickets = Ticket.objects.filter(company=user.company)
            ratings = TicketRating.objects.filter(ticket__company=user.company)
        elif user.role in [User.Role.CLIENT_USER]:
            tickets = Ticket.objects.filter(creator=user)
            ratings = TicketRating.objects.filter(ticket__creator=user)
        else:
             # IT Staff sees all
             tickets = Ticket.objects.all()
             ratings = TicketRating.objects.all()

        # Tickets by status
        status_counts = tickets.values('status').annotate(count=Count('id'))

        # Workload (Tickets by assignee, only relevant for IT Staff view)
        workload = []
        if user.role in [User.Role.IT_SPECIALIST, User.Role.IT_ADMIN]:
            workload = tickets.filter(status__in=[Ticket.Status.OPEN, Ticket.Status.IN_PROGRESS]).values(
                'assignee__email'
            ).annotate(count=Count('id')).order_by('-count')

        # Average resolution time
        resolved_tickets = tickets.filter(status=Ticket.Status.RESOLVED, resolved_at__isnull=False)
        avg_res_time = resolved_tickets.annotate(
            duration=ExpressionWrapper(F('resolved_at') - F('created_at'), output_field=DurationField())
        ).aggregate(avg_time=Avg('duration'))['avg_time']

        if avg_res_time:
             avg_res_time = str(avg_res_time)

        # SLA Violation (simplified as tickets where resolved_at > resolution_deadline)
        total_resolved_with_deadline = resolved_tickets.filter(resolution_deadline__isnull=False).count()
        violated_sla = resolved_tickets.filter(resolution_deadline__isnull=False, resolved_at__gt=F('resolution_deadline')).count()

        sla_violation_pct = 0
        if total_resolved_with_deadline > 0:
             sla_violation_pct = (violated_sla / total_resolved_with_deadline) * 100

        # Average Client Rating
        avg_rating = ratings.aggregate(avg=Avg('rating'))['avg']

        return Response({
            'status_counts': status_counts,
            'workload': workload,
            'average_resolution_time': avg_res_time,
            'sla_violation_percentage': round(sla_violation_pct, 2),
            'average_rating': round(avg_rating, 2) if avg_rating else None
        }, status=status.HTTP_200_OK)
