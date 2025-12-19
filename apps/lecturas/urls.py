"""URLs del módulo de lecturas"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'temperaturas', views.LecturaTemperaturaViewSet, basename='lectura')
router.register(r'resumen-diario', views.ResumenDiarioCamaraViewSet, basename='resumen')

urlpatterns = [
    path('', include(router.urls)),
]
