"""
URLs del módulo de sucursales
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'', views.SucursalViewSet, basename='sucursal')

urlpatterns = [
    path('', include(router.urls)),
]
