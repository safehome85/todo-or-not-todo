from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from users.models import Company
from datetime import timedelta
from django.utils import timezone

class SLA(models.Model):
    class Priority(models.TextChoices):
        LOW = 'low', _('Low')
        MEDIUM = 'medium', _('Medium')
        HIGH = 'high', _('High')
        CRITICAL = 'critical', _('Critical')

    priority = models.CharField(max_length=20, choices=Priority.choices, unique=True)
    response_time_minutes = models.PositiveIntegerField(help_text=_("Time to respond in minutes"))
    resolution_time_minutes = models.PositiveIntegerField(help_text=_("Time to resolve in minutes"))

    def __str__(self):
        return f"{self.priority} SLA"

class TicketCategory(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name

class Ticket(models.Model):
    class Status(models.TextChoices):
        OPEN = 'open', _('Open')
        IN_PROGRESS = 'in_progress', _('In Progress')
        RESOLVED = 'resolved', _('Resolved')
        CLOSED = 'closed', _('Closed')

    title = models.CharField(max_length=255)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    priority = models.CharField(max_length=20, choices=SLA.Priority.choices, default=SLA.Priority.LOW)

    category = models.ForeignKey(TicketCategory, on_delete=models.SET_NULL, null=True, blank=True)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='tickets')

    creator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='created_tickets')
    assignee = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_tickets')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    response_deadline = models.DateTimeField(null=True, blank=True)
    resolution_deadline = models.DateTimeField(null=True, blank=True)

    first_response_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"[{self.id}] {self.title}"

    def save(self, *args, **kwargs):
        if not self.pk:
            try:
                sla = SLA.objects.get(priority=self.priority)
                now = timezone.now()
                self.response_deadline = now + timedelta(minutes=sla.response_time_minutes)
                self.resolution_deadline = now + timedelta(minutes=sla.resolution_time_minutes)
            except SLA.DoesNotExist:
                pass
        super().save(*args, **kwargs)


class TicketComment(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Comment on {self.ticket} by {self.author}"

class TicketRating(models.Model):
    ticket = models.OneToOneField(Ticket, on_delete=models.CASCADE, related_name='rating')
    client = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    rating = models.PositiveSmallIntegerField(choices=[(i, str(i)) for i in range(1, 6)])
    feedback = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Rating {self.rating}/5 for {self.ticket}"
