"""Serializers de Eventos"""

from rest_framework import serializers
from .models import EventoTemperatura


class EventoTemperaturaSerializer(serializers.ModelSerializer):
    camara_nombre = serializers.CharField(source='camara.nombre', read_only=True)
    sucursal_nombre = serializers.CharField(source='camara.sucursal.nombre', read_only=True)
    sucursal_id = serializers.IntegerField(source='camara.sucursal.id', read_only=True)
    
    class Meta:
        model = EventoTemperatura
        fields = '__all__'
