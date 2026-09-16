from django.db.models.signals import post_save
from django.dispatch import receiver
from tickets.models import Ticket, TicketComment
from .models import Notification
from users.models import User

@receiver(post_save, sender=Ticket)
def notify_on_ticket_update(sender, instance, created, **kwargs):
    if created:
        # Notify IT Specialists and Admins about a new ticket
        it_staff = User.objects.filter(role__in=[User.Role.IT_SPECIALIST, User.Role.IT_ADMIN])
        for staff in it_staff:
            Notification.objects.create(
                user=staff,
                ticket=instance,
                message=f"New ticket created: {instance.title} (Priority: {instance.priority})"
            )
        # Notify the client admin of the company
        client_admins = User.objects.filter(company=instance.company, role=User.Role.CLIENT_ADMIN)
        for admin in client_admins:
             Notification.objects.create(
                user=admin,
                ticket=instance,
                message=f"New ticket created by {instance.creator.email}: {instance.title}"
            )
    else:
         # Simplified status change notification to the creator
         Notification.objects.create(
             user=instance.creator,
             ticket=instance,
             message=f"Ticket '{instance.title}' has been updated to status: {instance.status}"
         )

@receiver(post_save, sender=TicketComment)
def notify_on_new_comment(sender, instance, created, **kwargs):
    if created:
        ticket = instance.ticket
        author = instance.author

        # If a client comments, notify the assignee or all IT staff if unassigned
        if author.role in [User.Role.CLIENT_USER, User.Role.CLIENT_ADMIN]:
             if ticket.assignee:
                 Notification.objects.create(
                     user=ticket.assignee, ticket=ticket, message=f"New comment from client on ticket {ticket.id}"
                 )
             else:
                 it_staff = User.objects.filter(role__in=[User.Role.IT_SPECIALIST, User.Role.IT_ADMIN])
                 for staff in it_staff:
                     Notification.objects.create(
                         user=staff, ticket=ticket, message=f"New comment on unassigned ticket {ticket.id}"
                     )
        # If IT staff comments, notify the ticket creator
        elif author.role in [User.Role.IT_SPECIALIST, User.Role.IT_ADMIN]:
              Notification.objects.create(
                     user=ticket.creator, ticket=ticket, message=f"New comment from IT Support on your ticket {ticket.id}"
              )
