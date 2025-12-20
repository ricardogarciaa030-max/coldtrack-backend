"""
Firebase Authentication Middleware

Este middleware intercepta todas las requests y valida el token de Firebase.
Si el token es válido, agrega el usuario al request.

Flujo:
1. Extrae el token del header Authorization
2. Valida el token con Firebase Admin SDK
3. Obtiene el uid del usuario
4. Busca el usuario en la base de datos
5. Agrega el usuario al request.user
"""

from django.utils.deprecation import MiddlewareMixin
from django.http import JsonResponse
from firebase_admin import auth as firebase_auth
from services.firebase_service import initialize_firebase
from services.supabase_service import get_supabase_client
import logging

logger = logging.getLogger(__name__)


class FirebaseAuthMiddleware(MiddlewareMixin):
    """
    Middleware para autenticación con Firebase.
    
    Valida el token JWT de Firebase en cada request y carga
    los datos del usuario desde Supabase.
    """
    
    # Rutas que no requieren autenticación
    EXEMPT_URLS = [
        '/admin/',
        '/api/auth/',           # Todos los endpoints de auth
        '/api/test/',           # Endpoints de testing
        '/api/sync/users/',     # Sincronización de usuarios
        '/api/init/',           # Inicialización de datos
        '/',                    # API root
        '/api/',                # API root con prefijo
    ]
    
    def process_request(self, request):
        """
        Procesa cada request para validar autenticación.
        
        Args:
            request: HttpRequest de Django
        
        Returns:
            None si la autenticación es exitosa
            JsonResponse con error si falla
        """
        # Verificar si la ruta está exenta de autenticación
        is_exempt = any(request.path.startswith(url) for url in self.EXEMPT_URLS)
        
        # Para rutas exentas, aún intentamos procesar la autenticación si hay token
        # pero no devolvemos error si no hay token
        
        # Extraer token del header Authorization
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        
        if not auth_header.startswith('Bearer '):
            # Si no hay token y la ruta está exenta, continuar sin autenticación
            request.firebase_user = None
            if is_exempt:
                return None
            # Si no es exenta, permitir que Django REST Framework maneje el error
            return None
        
        token = auth_header.split('Bearer ')[1]
        
        try:
            # Inicializar Firebase si no está inicializado
            initialize_firebase()
            
            # Verificar el token con Firebase
            decoded_token = firebase_auth.verify_id_token(token)
            uid = decoded_token['uid']
            
            # Buscar usuario en Supabase usando service_key para bypass RLS
            client = get_supabase_client(use_service_key=True)
            response = client.table('usuarios')\
                .select('*')\
                .eq('firebase_uid', uid)\
                .eq('activo', True)\
                .execute()
            
            if response.data and len(response.data) > 0:
                user_data = response.data[0]
                
                # Agregar datos del usuario al request
                request.firebase_user = {
                    'uid': uid,
                    'id': user_data['id'],
                    'email': user_data['email'],
                    'nombre': user_data['nombre'],
                    'rol': user_data['rol'],
                    'sucursal_id': user_data.get('sucursal_id'),
                }
                
                logger.debug(f"Usuario autenticado: {user_data['email']} ({user_data['rol']})")
                return None
            else:
                logger.warning(f"Usuario con uid {uid} no encontrado en base de datos")
                request.firebase_user = None
                if is_exempt:
                    return None
                return JsonResponse({
                    'error': 'Usuario no encontrado en el sistema'
                }, status=404)
        
        except firebase_auth.InvalidIdTokenError:
            logger.warning("Token de Firebase inválido")
            request.firebase_user = None
            if is_exempt:
                return None
            return JsonResponse({
                'error': 'Token inválido'
            }, status=401)
        
        except firebase_auth.ExpiredIdTokenError:
            logger.warning("Token de Firebase expirado")
            request.firebase_user = None
            if is_exempt:
                return None
            return JsonResponse({
                'error': 'Token expirado'
            }, status=401)
        
        except Exception as e:
            logger.error(f"Error en autenticación: {str(e)}")
            request.firebase_user = None
            if is_exempt:
                return None
            return JsonResponse({
                'error': 'Error de autenticación'
            }, status=500)
