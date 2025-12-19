"""URLs del módulo de cámaras"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'', views.CamaraFrioViewSet, basename='camara')

urlpatterns = [
    path('', include(router.urls)),
]
