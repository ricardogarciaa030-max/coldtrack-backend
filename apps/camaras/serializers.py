"""Serializers de Cámaras"""

from rest_framework import serializers
from .models import CamaraFrio
from apps.sucursales.serializers import SucursalSerializer


class CamaraFrioSerializer(serializers.ModelSerializer):
    """Serializer para CamaraFrio"""
    
    sucursal_data = SucursalSerializer(source='sucursal', read_only=True)
    
    class Meta:
        model = CamaraFrio
        fields = ['id', 'created_at', 'sucursal', 'sucursal_data', 'nombre', 
                  'codigo', 'firebase_path', 'tipo', 'activa']
        read_only_fields = ['id', 'created_at']
