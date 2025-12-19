"""Vistas de Usuarios - CRUD con permisos de ADMIN"""

from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.decorators import api_view
from .serializers import UsuarioSerializer
from apps.auth.permissions import IsAdmin
from services.supabase_service import get_supabase_client
from firebase_admin import auth as firebase_auth
from services.firebase_service import initialize_firebase
import logging

logger = logging.getLogger(__name__)


@api_view(['POST'])
def create_user_test(request):
    """Vista de prueba para crear usuarios"""
    print(f"🧪 TEST CREATE USER - Datos recibidos: {request.data}")
    logger.info(f"🧪 Test create user: {request.data}")
    
    try:
        # Inicializar Firebase
        initialize_firebase()
        
        # Datos de prueba
        email = request.data.get('email', 'test@example.com')
        password = request.data.get('password', '123456')
        nombre = request.data.get('nombre', 'Test User')
        
        # Crear usuario en Firebase Auth
        firebase_user = firebase_auth.create_user(
            email=email,
            password=password,
            display_name=nombre
        )
        
        print(f"✅ Usuario creado en Firebase: {firebase_user.uid}")
        
        return Response({
            'success': True,
            'firebase_uid': firebase_user.uid,
            'email': email,
            'message': 'Usuario creado exitosamente en Firebase'
        })
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return Response({
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UsuarioViewSet(viewsets.ViewSet):
    """ViewSet para gestionar usuarios desde Supabase - Solo ADMIN"""
    
    permission_classes = [IsAdmin]  # Solo ADMIN puede gestionar usuarios
    
    @action(detail=False, methods=['get'])
    def test_auth(self, request):
        """Endpoint de prueba para verificar autenticación"""
        try:
            logger.info(f"🔍 Test de autenticación - Usuario: {getattr(request, 'firebase_user', 'No autenticado')}")
            
            if hasattr(request, 'firebase_user') and request.firebase_user:
                return Response({
                    'authenticated': True,
                    'user': request.firebase_user,
                    'message': 'Usuario autenticado correctamente'
                })
            else:
                return Response({
                    'authenticated': False,
                    'message': 'Usuario no autenticado'
                }, status=status.HTTP_401_UNAUTHORIZED)
                
        except Exception as e:
            logger.error(f"Error en test de autenticación: {str(e)}")
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def list(self, request):
        """Lista todos los usuarios desde Supabase"""
        try:
            client = get_supabase_client(use_service_key=True)
            
            # Construir query con JOIN para traer datos de sucursal
            query = client.table('usuarios').select('*, sucursal_data:sucursales(id, nombre)')
            
            # Filtros opcionales
            sucursal_id = request.query_params.get('sucursal_id')
            if sucursal_id:
                query = query.eq('sucursal_id', sucursal_id)
            
            rol = request.query_params.get('rol')
            if rol:
                query = query.eq('rol', rol)
            
            # Ejecutar query
            response = query.execute()
            
            logger.info(f"Usuarios obtenidos: {len(response.data) if response.data else 0}")
            
            return Response(response.data if response.data else [])
            
        except Exception as e:
            logger.error(f"Error al obtener usuarios: {str(e)}")
            return Response(
                {'error': 'Error al obtener usuarios'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def retrieve(self, request, pk=None):
        """Obtiene un usuario específico"""
        try:
            client = get_supabase_client(use_service_key=True)
            response = client.table('usuarios').select('*').eq('id', pk).execute()
            
            if response.data and len(response.data) > 0:
                return Response(response.data[0])
            else:
                return Response(
                    {'error': 'Usuario no encontrado'},
                    status=status.HTTP_404_NOT_FOUND
                )
                
        except Exception as e:
            logger.error(f"Error al obtener usuario {pk}: {str(e)}")
            return Response(
                {'error': 'Error al obtener usuario'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def create(self, request):
        """Crea un nuevo usuario en Firebase Auth y lo sincroniza a Supabase"""
        try:
            logger.info(f"🚀 Iniciando creación de usuario: {request.data.get('email')}")
            
            # Inicializar Firebase
            initialize_firebase()
            
            # Validar datos requeridos
            required_fields = ['email', 'nombre', 'rol', 'password']
            for field in required_fields:
                if field not in request.data:
                    logger.error(f"❌ Campo requerido faltante: {field}")
                    return Response(
                        {'error': f'Campo requerido: {field}'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            email = request.data['email']
            password = request.data['password']
            nombre = request.data['nombre']
            rol = request.data['rol']
            sucursal_id = request.data.get('sucursal_id')
            activo = request.data.get('activo', True)
            
            # 1. Crear usuario en Firebase Auth
            try:
                firebase_user = firebase_auth.create_user(
                    email=email,
                    password=password,
                    display_name=nombre,
                    disabled=not activo
                )
                logger.info(f"Usuario creado en Firebase Auth: {firebase_user.uid}")
                
            except Exception as firebase_error:
                logger.error(f"Error al crear usuario en Firebase: {str(firebase_error)}")
                return Response(
                    {'error': f'Error al crear usuario en Firebase: {str(firebase_error)}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # 2. Crear usuario en Supabase
            try:
                client = get_supabase_client(use_service_key=True)
                
                user_data = {
                    'firebase_uid': firebase_user.uid,
                    'email': email,
                    'nombre': nombre,
                    'rol': rol,
                    'sucursal_id': sucursal_id,
                    'activo': activo
                }
                
                response = client.table('usuarios').insert(user_data).execute()
                
                if response.data and len(response.data) > 0:
                    logger.info(f"Usuario sincronizado a Supabase: {email}")
                    return Response(response.data[0], status=status.HTTP_201_CREATED)
                else:
                    # Si falla Supabase, eliminar usuario de Firebase
                    firebase_auth.delete_user(firebase_user.uid)
                    return Response(
                        {'error': 'Error al sincronizar usuario a Supabase'},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR
                    )
                    
            except Exception as supabase_error:
                # Si falla Supabase, eliminar usuario de Firebase
                try:
                    firebase_auth.delete_user(firebase_user.uid)
                except:
                    pass
                
                logger.error(f"Error al crear usuario en Supabase: {str(supabase_error)}")
                return Response(
                    {'error': f'Error al sincronizar usuario: {str(supabase_error)}'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
                
        except Exception as e:
            logger.error(f"Error general al crear usuario: {str(e)}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def update(self, request, pk=None):
        """Actualiza un usuario existente en Supabase y Firebase Auth"""
        try:
            initialize_firebase()
            client = get_supabase_client(use_service_key=True)
            
            # Obtener usuario actual para obtener firebase_uid
            current_user_response = client.table('usuarios')\
                .select('firebase_uid')\
                .eq('id', pk)\
                .execute()
            
            if not current_user_response.data or len(current_user_response.data) == 0:
                return Response(
                    {'error': 'Usuario no encontrado'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            firebase_uid = current_user_response.data[0]['firebase_uid']
            
            # Preparar datos para actualizar
            update_data = {
                'nombre': request.data.get('nombre'),
                'email': request.data.get('email'),
                'rol': request.data.get('rol'),
                'sucursal_id': request.data.get('sucursal_id'),
                'activo': request.data.get('activo', True)
            }
            
            # Remover campos None
            update_data = {k: v for k, v in update_data.items() if v is not None}
            
            # Si hay contraseña nueva, actualizar en Firebase Auth
            if 'password' in request.data and request.data['password']:
                try:
                    firebase_auth.update_user(
                        firebase_uid,
                        password=request.data['password'],
                        display_name=update_data.get('nombre'),
                        disabled=not update_data.get('activo', True)
                    )
                    logger.info(f"Usuario actualizado en Firebase Auth: {firebase_uid}")
                except Exception as firebase_error:
                    logger.error(f"Error al actualizar usuario en Firebase: {str(firebase_error)}")
                    return Response(
                        {'error': f'Error al actualizar en Firebase: {str(firebase_error)}'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            # Actualizar en Supabase
            response = client.table('usuarios')\
                .update(update_data)\
                .eq('id', pk)\
                .execute()
            
            if response.data and len(response.data) > 0:
                logger.info(f"Usuario actualizado en Supabase: {pk}")
                return Response(response.data[0])
            else:
                return Response(
                    {'error': 'Error al actualizar usuario'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
                
        except Exception as e:
            logger.error(f"Error al actualizar usuario {pk}: {str(e)}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def destroy(self, request, pk=None):
        """Elimina completamente un usuario de Supabase y Firebase Auth"""
        try:
            initialize_firebase()
            client = get_supabase_client(use_service_key=True)
            
            # Obtener firebase_uid antes de eliminar
            current_user_response = client.table('usuarios')\
                .select('firebase_uid, email')\
                .eq('id', pk)\
                .execute()
            
            if not current_user_response.data or len(current_user_response.data) == 0:
                return Response(
                    {'error': 'Usuario no encontrado'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            firebase_uid = current_user_response.data[0]['firebase_uid']
            email = current_user_response.data[0]['email']
            
            # Eliminar completamente de Firebase Auth
            try:
                firebase_auth.delete_user(firebase_uid)
                logger.info(f"Usuario eliminado de Firebase Auth: {firebase_uid} ({email})")
            except Exception as firebase_error:
                logger.warning(f"Error al eliminar usuario de Firebase: {str(firebase_error)}")
                # Continuar con Supabase aunque falle Firebase
            
            # Eliminar completamente de Supabase
            response = client.table('usuarios')\
                .delete()\
                .eq('id', pk)\
                .execute()
            
            if response.data is not None:  # DELETE puede devolver lista vacía si es exitoso
                logger.info(f"Usuario eliminado completamente de Supabase: {pk} ({email})")
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                return Response(
                    {'error': 'Error al eliminar usuario de Supabase'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
                
        except Exception as e:
            logger.error(f"Error al eliminar usuario {pk}: {str(e)}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
