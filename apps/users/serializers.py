"""Serializers de Usuarios"""

from rest_framework import serializers
from .models import Usuario
from apps.sucursales.serializers import SucursalSerializer


class UsuarioSerializer(serializers.ModelSerializer):
    """Serializer para Usuario"""
    
    sucursal_data = SucursalSerializer(source='sucursal', read_only=True)
    
    class Meta:
        model = Usuario
        fields = ['id', 'created_at', 'firebase_uid', 'email', 'nombre', 
                  'rol', 'sucursal', 'sucursal_data', 'activo']
        read_only_fields = ['id', 'created_at']
