"""
URLs del módulo de autenticación
"""

from django.urls import path
from . import views

urlpatterns = [
    path('verify-token/', views.verify_token, name='verify-token'),
    path('me/', views.get_current_user, name='current-user'),
]
