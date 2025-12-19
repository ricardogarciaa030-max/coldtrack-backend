"""URLs del módulo de usuarios"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'', views.UsuarioViewSet, basename='usuario')

urlpatterns = [
    path('test/', views.create_user_test, name='create_user_test'),
    path('', include(router.urls)),
]
