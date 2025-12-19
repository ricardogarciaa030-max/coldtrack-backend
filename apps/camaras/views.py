"""Vistas de Cámaras - CRUD con permisos"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from apps.auth.permissions import IsAdmin
from services.firebase_service import get_live_status
from services.supabase_service import get_supabase_client
import logging

logger = logging.getLogger(__name__)


class CamaraFrioViewSet(viewsets.ViewSet):
    """ViewSet para gestionar cámaras de frío desde Supabase"""
    
    def get_permissions(self):
        """Solo ADMIN puede crear/editar/eliminar"""
        if self.action in ['create', 'update', 'destroy']:
            return [IsAdmin()]
        return []
    
    def list(self, request):
        """Lista todas las cámaras"""
        try:
            client = get_supabase_client(use_service_key=True)
            
            # Construir query con JOIN para traer datos de sucursal
            query = client.table('camaras_frio').select('*, sucursal:sucursales(id, nombre)')
            
            # Filtrar por rol del usuario
            user = request.firebase_user if hasattr(request, 'firebase_user') else None
            if user and user.get('rol') != 'ADMIN':
                sucursal_id = user.get('sucursal_id')
                if sucursal_id:
                    query = query.eq('sucursal_id', sucursal_id)
                else:
                    return Response([])
            
            # Filtro opcional por sucursal
            sucursal_id = request.query_params.get('sucursal_id')
            if sucursal_id:
                query = query.eq('sucursal_id', sucursal_id)
            
            response = query.execute()
            
            logger.info(f"Cámaras obtenidas: {len(response.data) if response.data else 0}")
            
            return Response(response.data if response.data else [])
            
        except Exception as e:
            logger.error(f"Error al obtener cámaras: {str(e)}")
            return Response(
                {'error': 'Error al obtener cámaras'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def retrieve(self, request, pk=None):
        """Obtiene una cámara específica"""
        try:
            client = get_supabase_client(use_service_key=True)
            response = client.table('camaras_frio')\
                .select('*, sucursal:sucursales(id, nombre)')\
                .eq('id', pk)\
                .execute()
            
            if response.data and len(response.data) > 0:
                return Response(response.data[0])
            else:
                return Response(
                    {'error': 'Cámara no encontrada'},
                    status=status.HTTP_404_NOT_FOUND
                )
                
        except Exception as e:
            logger.error(f"Error al obtener cámara {pk}: {str(e)}")
            return Response(
                {'error': 'Error al obtener cámara'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def create(self, request):
        """Crea una nueva cámara"""
        try:
            client = get_supabase_client(use_service_key=True)
            
            response = client.table('camaras_frio').insert(request.data).execute()
            
            if response.data and len(response.data) > 0:
                logger.info(f"Cámara creada: {response.data[0]['nombre']}")
                return Response(response.data[0], status=status.HTTP_201_CREATED)
            else:
                return Response(
                    {'error': 'Error al crear cámara'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
                
        except Exception as e:
            logger.error(f"Error al crear cámara: {str(e)}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def update(self, request, pk=None):
        """Actualiza una cámara existente"""
        try:
            client = get_supabase_client(use_service_key=True)
            
            response = client.table('camaras_frio')\
                .update(request.data)\
                .eq('id', pk)\
                .execute()
            
            if response.data and len(response.data) > 0:
                logger.info(f"Cámara actualizada: {pk}")
                return Response(response.data[0])
            else:
                return Response(
                    {'error': 'Cámara no encontrada'},
                    status=status.HTTP_404_NOT_FOUND
                )
                
        except Exception as e:
            logger.error(f"Error al actualizar cámara {pk}: {str(e)}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def destroy(self, request, pk=None):
        """Elimina (desactiva) una cámara"""
        try:
            client = get_supabase_client(use_service_key=True)
            
            # Desactivar en lugar de eliminar
            response = client.table('camaras_frio')\
                .update({'activa': False})\
                .eq('id', pk)\
                .execute()
            
            if response.data and len(response.data) > 0:
                logger.info(f"Cámara desactivada: {pk}")
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                return Response(
                    {'error': 'Cámara no encontrada'},
                    status=status.HTTP_404_NOT_FOUND
                )
                
        except Exception as e:
            logger.error(f"Error al eliminar cámara {pk}: {str(e)}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['get'])
    def live_status(self, request, pk=None):
        """
        Obtiene el estado en vivo de una cámara desde Firebase.
        
        GET /api/camaras/{id}/live_status/
        """
        try:
            # Obtener cámara de Supabase
            client = get_supabase_client(use_service_key=True)
            response = client.table('camaras_frio').select('*').eq('id', pk).execute()
            
            if not response.data or len(response.data) == 0:
                return Response(
                    {'error': 'Cámara no encontrada'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            camara = response.data[0]
            
            # Obtener estado en vivo desde Firebase
            live_status = get_live_status(camara['firebase_path'])
            
            if live_status:
                return Response({
                    'camara_id': camara['id'],
                    'camara_nombre': camara['nombre'],
                    'status': live_status
                })
            else:
                return Response({
                    'error': 'No hay datos en vivo disponibles'
                }, status=status.HTTP_404_NOT_FOUND)
                
        except Exception as e:
            logger.error(f"Error al obtener estado en vivo: {str(e)}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
