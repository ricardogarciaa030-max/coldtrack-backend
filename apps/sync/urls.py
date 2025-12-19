"""
URLs para sincronización
"""
from django.urls import path
from . import views

urlpatterns = [
    path('trigger/', views.trigger_sync, name='trigger-sync'),
]
