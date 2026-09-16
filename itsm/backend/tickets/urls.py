from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TicketViewSet, TicketCategoryViewSet, SLAViewSet

router = DefaultRouter()
router.register(r'tickets', TicketViewSet, basename='ticket')
router.register(r'categories', TicketCategoryViewSet, basename='ticketcategory')
router.register(r'slas', SLAViewSet, basename='sla')

urlpatterns = [
    path('', include(router.urls)),
]
