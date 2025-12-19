"""Vistas de Lecturas - Consulta de histórico"""

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Avg, Min, Max, Count
from .models import LecturaTemperatura, ResumenDiarioCamara
from .serializers import LecturaTemperaturaSerializer, ResumenDiarioCamaraSerializer
from apps.auth.permissions import filter_by_sucursal


class LecturaTemperaturaViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet para consultar lecturas de temperatura"""
    
    queryset = LecturaTemperatura.objects.select_related('camara', 'camara__sucursal').all()
    serializer_class = LecturaTemperaturaSerializer
    
    def get_queryset(self):
        """Filtra por sucursal y permite filtros adicionales"""
        queryset = super().get_queryset()
        
        if hasattr(self.request, 'firebase_user'):
            queryset = filter_by_sucursal(queryset, self.request.firebase_user)
        
        # Filtros opcionales
        camara_id = self.request.query_params.get('camara_id')
        if camara_id:
            queryset = queryset.filter(camara_id=camara_id)
        
        fecha_desde = self.request.query_params.get('fecha_desde')
        if fecha_desde:
            queryset = queryset.filter(timestamp__gte=fecha_desde)
        
        fecha_hasta = self.request.query_params.get('fecha_hasta')
        if fecha_hasta:
            queryset = queryset.filter(timestamp__lte=fecha_hasta)
        
        return queryset


class ResumenDiarioCamaraViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet para consultar resúmenes diarios"""
    
    queryset = ResumenDiarioCamara.objects.select_related('camara', 'camara__sucursal').all()
    serializer_class = ResumenDiarioCamaraSerializer
    
    def get_queryset(self):
        """Filtra por sucursal y permite filtros adicionales"""
        queryset = super().get_queryset()
        
        if hasattr(self.request, 'firebase_user'):
            queryset = filter_by_sucursal(queryset, self.request.firebase_user)
        
        # Filtros opcionales
        camara_id = self.request.query_params.get('camara_id')
        if camara_id:
            queryset = queryset.filter(camara_id=camara_id)
        
        fecha_desde = self.request.query_params.get('fecha_desde')
        if fecha_desde:
            queryset = queryset.filter(fecha__gte=fecha_desde)
        
        fecha_hasta = self.request.query_params.get('fecha_hasta')
        if fecha_hasta:
            queryset = queryset.filter(fecha__lte=fecha_hasta)
        
        return queryset
