"""Vistas de Eventos - Consulta y gestión de eventos"""

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Count, Q
from datetime import datetime, timedelta
from .models import EventoTemperatura
from .serializers import EventoTemperaturaSerializer
from apps.auth.permissions import filter_by_sucursal, CanEditSucursal


class EventoTemperaturaViewSet(viewsets.ModelViewSet):
    """ViewSet para gestionar eventos de temperatura"""
    
    queryset = EventoTemperatura.objects.select_related('camara', 'camara__sucursal').all()
    serializer_class = EventoTemperaturaSerializer
    
    def get_queryset(self):
        """Filtra por sucursal y permite filtros adicionales"""
        queryset = super().get_queryset()
        
        if hasattr(self.request, 'firebase_user'):
            queryset = filter_by_sucursal(queryset, self.request.firebase_user)
        
        # Filtros opcionales
        camara_id = self.request.query_params.get('camara_id')
        if camara_id:
            queryset = queryset.filter(camara_id=camara_id)
        
        tipo = self.request.query_params.get('tipo')
        if tipo:
            queryset = queryset.filter(tipo=tipo)
        
        estado = self.request.query_params.get('estado')
        if estado:
            queryset = queryset.filter(estado=estado)
        
        fecha_desde = self.request.query_params.get('fecha_desde')
        if fecha_desde:
            queryset = queryset.filter(fecha_inicio__gte=fecha_desde)
        
        fecha_hasta = self.request.query_params.get('fecha_hasta')
        if fecha_hasta:
            queryset = queryset.filter(fecha_inicio__lte=fecha_hasta)
        
        return queryset
    
    def get_permissions(self):
        """ENCARGADO puede editar observaciones, SUBJEFE solo lectura"""
        if self.action in ['update', 'partial_update']:
            return [CanEditSucursal()]
        return super().get_permissions()
    
    @action(detail=False, methods=['get'])
    def recientes(self, request):
        """
        Obtiene eventos recientes (últimas 24 horas).
        
        GET /api/eventos/recientes/
        """
        hace_24h = datetime.now() - timedelta(hours=24)
        queryset = self.get_queryset().filter(fecha_inicio__gte=hace_24h)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def en_curso(self, request):
        """
        Obtiene eventos que están actualmente en curso.
        
        GET /api/eventos/en_curso/
        """
        queryset = self.get_queryset().filter(fecha_fin__isnull=True)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
