"""
Vistas de Autenticación

Endpoints para validar tokens de Firebase y obtener información del usuario.
"""

from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from firebase_admin import auth as firebase_auth
from services.firebase_service import initialize_firebase
from services.supabase_service import get_supabase_client
import logging

logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([])  # No requiere autenticación previa
def verify_token(request):
    """
    Verifica un token de Firebase y retorna información del usuario.
    """
    token = request.data.get('token')
    
    if not token:
        return Response({
            'error': 'Token no proporcionado'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Inicializar Firebase
        initialize_firebase()
        
        # Verificar token
        decoded_token = firebase_auth.verify_id_token(token)
        uid = decoded_token['uid']
        email = decoded_token.get('email', '')
        
        # Buscar usuario en Supabase usando service_key para bypass RLS
        client = get_supabase_client(use_service_key=True)
        response = client.table('usuarios')\
            .select('*')\
            .eq('firebase_uid', uid)\
            .eq('activo', True)\
            .execute()
        
        if response.data and len(response.data) > 0:
            user_data = response.data[0]
            
            logger.info(f"Token verificado para usuario: {user_data['email']}")
            
            return Response({
                'user': {
                    'uid': uid,
                    'id': user_data['id'],
                    'email': user_data['email'],
                    'nombre': user_data['nombre'],
                    'rol': user_data['rol'],
                    'sucursal_id': user_data.get('sucursal_id'),
                }
            }, status=status.HTTP_200_OK)
        else:
            logger.warning(f"Usuario con uid {uid} no encontrado en base de datos")
            return Response({
                'error': 'Usuario no encontrado en el sistema'
            }, status=status.HTTP_404_NOT_FOUND)
    
    except firebase_auth.InvalidIdTokenError:
        logger.warning("Token de Firebase inválido")
        return Response({
            'error': 'Token inválido'
        }, status=status.HTTP_401_UNAUTHORIZED)
    
    except firebase_auth.ExpiredIdTokenError:
        logger.warning("Token de Firebase expirado")
        return Response({
            'error': 'Token expirado'
        }, status=status.HTTP_401_UNAUTHORIZED)
    
    except Exception as e:
        logger.error(f"Error al verificar token: {str(e)}")
        return Response({
            'error': 'Error al verificar token'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def get_current_user(request):
    """
    Obtiene información del usuario actualmente autenticado.
    
    Este endpoint requiere autenticación (token en header).
    
    Response:
        {
            "user": {
                "uid": "firebase_uid",
                "id": 1,
                "email": "usuario@example.com",
                "nombre": "Juan Pérez",
                "rol": "ADMIN",
                "sucursal_id": 1
            }
        }
    
    Errors:
        401: No autenticado
    """
    if not hasattr(request, 'firebase_user') or request.firebase_user is None:
        return Response({
            'error': 'No autenticado'
        }, status=status.HTTP_401_UNAUTHORIZED)
    
    return Response({
        'user': request.firebase_user
    }, status=status.HTTP_200_OK)
