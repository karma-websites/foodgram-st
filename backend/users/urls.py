from rest_framework.routers import DefaultRouter
from .views import UserViewSet
from django.urls import path

from . import views

# /api/users
router = DefaultRouter()
router.register('', UserViewSet, basename='users')