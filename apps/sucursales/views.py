"""
Vistas de Sucursales

CRUD de sucursales con permisos basados en roles.
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from apps.auth.permissions import IsAdmin
from services.supabase_service import get_supabase_client
import logging

logger = logging.getLogger(__name__)


class SucursalViewSet(viewsets.ViewSet):
    """
    ViewSet para gestionar sucursales desde Supabase.
    
    Endpoints:
        GET /api/sucursales/ - Lista todas las sucursales
        POST /api/sucursales/ - Crea una nueva sucursal (solo ADMIN)
        GET /api/sucursales/{id}/ - Obtiene una sucursal específica
        PUT /api/sucursales/{id}/ - Actualiza una sucursal (solo ADMIN)
        DELETE /api/sucursales/{id}/ - Elimina una sucursal (solo ADMIN)
        GET /api/sucursales/activas/ - Lista solo sucursales activas
    
    Permisos:
        - ADMIN: Acceso total
        - ENCARGADO/SUBJEFE: Solo lectura de su sucursal
    """
    
    def get_permissions(self):
        """Define permisos según la acción"""
        if self.action in ['create', 'update', 'destroy']:
            return [IsAdmin()]
        return []
    
    def list(self, request):
        """Lista todas las sucursales"""
        try:
            client = get_supabase_client(use_service_key=True)
            
            # Construir query
            query = client.table('sucursales').select('*')
            
            # Filtrar por rol del usuario
            user = request.firebase_user if hasattr(request, 'firebase_user') else None
            if user and user.get('rol') != 'ADMIN':
                sucursal_id = user.get('sucursal_id')
                if sucursal_id:
                    query = query.eq('id', sucursal_id)
                else:
                    return Response([])
            
            response = query.execute()
            
            logger.info(f"Sucursales obtenidas: {len(response.data) if response.data else 0}")
            
            return Response(response.data if response.data else [])
            
        except Exception as e:
            logger.error(f"Error al obtener sucursales: {str(e)}")
            return Response(
                {'error': 'Error al obtener sucursales'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def retrieve(self, request, pk=None):
        """Obtiene una sucursal específica"""
        try:
            client = get_supabase_client(use_service_key=True)
            response = client.table('sucursales').select('*').eq('id', pk).execute()
            
            if response.data and len(response.data) > 0:
                return Response(response.data[0])
            else:
                return Response(
                    {'error': 'Sucursal no encontrada'},
                    status=status.HTTP_404_NOT_FOUND
                )
                
        except Exception as e:
            logger.error(f"Error al obtener sucursal {pk}: {str(e)}")
            return Response(
                {'error': 'Error al obtener sucursal'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def create(self, request):
        """Crea una nueva sucursal"""
        try:
            client = get_supabase_client(use_service_key=True)
            
            response = client.table('sucursales').insert(request.data).execute()
            
            if response.data and len(response.data) > 0:
                logger.info(f"Sucursal creada: {response.data[0]['nombre']}")
                return Response(response.data[0], status=status.HTTP_201_CREATED)
            else:
                return Response(
                    {'error': 'Error al crear sucursal'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
                
        except Exception as e:
            logger.error(f"Error al crear sucursal: {str(e)}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def update(self, request, pk=None):
        """Actualiza una sucursal existente"""
        try:
            client = get_supabase_client(use_service_key=True)
            
            response = client.table('sucursales')\
                .update(request.data)\
                .eq('id', pk)\
                .execute()
            
            if response.data and len(response.data) > 0:
                logger.info(f"Sucursal actualizada: {pk}")
                return Response(response.data[0])
            else:
                return Response(
                    {'error': 'Sucursal no encontrada'},
                    status=status.HTTP_404_NOT_FOUND
                )
                
        except Exception as e:
            logger.error(f"Error al actualizar sucursal {pk}: {str(e)}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def destroy(self, request, pk=None):
        """Elimina (desactiva) una sucursal"""
        try:
            client = get_supabase_client(use_service_key=True)
            
            # Desactivar en lugar de eliminar
            response = client.table('sucursales')\
                .update({'activa': False})\
                .eq('id', pk)\
                .execute()
            
            if response.data and len(response.data) > 0:
                logger.info(f"Sucursal desactivada: {pk}")
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                return Response(
                    {'error': 'Sucursal no encontrada'},
                    status=status.HTTP_404_NOT_FOUND
                )
                
        except Exception as e:
            logger.error(f"Error al eliminar sucursal {pk}: {str(e)}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def activas(self, request):
        """Lista solo sucursales activas"""
        try:
            client = get_supabase_client(use_service_key=True)
            
            query = client.table('sucursales').select('*').eq('activa', True)
            
            # Filtrar por rol del usuario
            user = request.firebase_user if hasattr(request, 'firebase_user') else None
            if user and user.get('rol') != 'ADMIN':
                sucursal_id = user.get('sucursal_id')
                if sucursal_id:
                    query = query.eq('id', sucursal_id)
                else:
                    return Response([])
            
            response = query.execute()
            
            return Response(response.data if response.data else [])
            
        except Exception as e:
            logger.error(f"Error al obtener sucursales activas: {str(e)}")
            return Response(
                {'error': 'Error al obtener sucursales activas'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
