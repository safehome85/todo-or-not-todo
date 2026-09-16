from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CompanyViewSet, UserViewSet, RegisterView

router = DefaultRouter()
router.register(r'companies', CompanyViewSet, basename='company')
router.register(r'users', UserViewSet, basename='user')

urlpatterns = [
    path('', include(router.urls)),
    path('register/', RegisterView.as_view(), name='register'),
]
