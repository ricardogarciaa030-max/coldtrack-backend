"""Serializers de Lecturas"""

from rest_framework import serializers
from .models import LecturaTemperatura, ResumenDiarioCamara


class LecturaTemperaturaSerializer(serializers.ModelSerializer):
    class Meta:
        model = LecturaTemperatura
        fields = '__all__'


class ResumenDiarioCamaraSerializer(serializers.ModelSerializer):
    camara_nombre = serializers.CharField(source='camara.nombre', read_only=True)
    sucursal_nombre = serializers.CharField(source='camara.sucursal.nombre', read_only=True)
    
    class Meta:
        model = ResumenDiarioCamara
        fields = '__all__'
