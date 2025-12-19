"""
Serializers de Sucursales

Valida y serializa datos de sucursales para la API.
"""

from rest_framework import serializers
from .models import Sucursal


class SucursalSerializer(serializers.ModelSerializer):
    """
    Serializer para el modelo Sucursal.
    
    Convierte objetos Sucursal a JSON y viceversa.
    """
    
    class Meta:
        model = Sucursal
        fields = ['id', 'created_at', 'nombre', 'direccion', 'descripcion', 'activa']
        read_only_fields = ['id', 'created_at']
