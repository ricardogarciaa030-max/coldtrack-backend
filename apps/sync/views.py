"""
Vistas para sincronización automática
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from datetime import date
from .services import sync_all_devices
from apps.auth.permissions import IsAdmin
import logging

logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([IsAdmin])
def trigger_sync(request):
    """
    Endpoint para disparar sincronización manual.
    
    POST /api/sync/trigger/
    
    Body (opcional):
        {
            "date": "2025-12-09"  // Si no se especifica, usa hoy
        }
    """
    try:
        date_str = request.data.get('date')
        target_date = date.today()
        
        if date_str:
            from datetime import datetime
            target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        
        logger.info(f"Sincronización manual disparada para {target_date}")
        
        result = sync_all_devices(target_date)
        
        return Response({
            'success': True,
            'message': 'Sincronización completada',
            'result': result
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error en sincronización manual: {str(e)}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
