"""URLs del módulo de eventos"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from .supabase_views import listar_eventos_supabase

# Router original (comentado temporalmente)
# router = DefaultRouter()
# router.register(r'', views.EventoTemperaturaViewSet, basename='evento')

urlpatterns = [
    # Vista que funciona con Supabase
    path('', listar_eventos_supabase, name='eventos-supabase'),
    
    # Router original (comentado)
    # path('', include(router.urls)),
]
