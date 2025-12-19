"""
Script para sincronizar TODOS los eventos del día actual desde Firebase
"""
import os
import django
import sys

# Configurar Django
sys.path.append(os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'coldtrack.settings')
django.setup()

from services.firebase_service import initialize_firebase
from services.supabase_service import get_camera_by_firebase_path, get_supabase_client
import firebase_admin
from firebase_admin import db
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def sync_all_events_today():
    """Sincronizar todos los eventos del día actual"""
    try:
        # Inicializar Firebase
        initialize_firebase()
        
        device_id = 'camara1'
        # Obtener todos los eventos del día 09 (hoy)
        events_ref = db.reference(f'eventos/{device_id}/2025/12/09')
        events_data = events_ref.get()
        
        if not events_data:
            logger.info("No hay eventos para sincronizar")
            return
        
        logger.info(f"Encontrados {len(events_data)} eventos para sincronizar")
        
        # Buscar cámara en Supabase
        camera = get_camera_by_firebase_path(device_id)
        if not camera:
            logger.error(f"Cámara no encontrada: {device_id}")
            return
        
        client = get_supabase_client(use_service_key=True)
        
        # Procesar cada evento
        for event_id, event_data in events_data.items():
            if not isinstance(event_data, dict):
                continue
                
            logger.info(f"\n--- Procesando evento {event_id} ---")
            
            # Extraer datos del evento
            start_ts = event_data.get('start_ts')
            end_ts = event_data.get('end_ts')
            duration_ms = event_data.get('duration_ms', 0)
            max_temp = event_data.get('max_temp', 0)
            event_type = event_data.get('type', 'FALLA')
            ended = event_data.get('ended', False)
            
            if not start_ts:
                logger.warning(f"Evento {event_id} sin start_ts, saltando")
                continue
            
            # Convertir timestamps
            fecha_inicio = datetime.fromtimestamp(start_ts)
            fecha_fin = None
            duracion_minutos = duration_ms // 60000 if duration_ms else 0
            estado = 'EN_CURSO'
            
            if ended and end_ts:
                fecha_fin = datetime.fromtimestamp(end_ts)
                estado = 'RESUELTO'
            
            logger.info(f"  - Tipo: {event_type}")
            logger.info(f"  - Inicio: {fecha_inicio}")
            logger.info(f"  - Fin: {fecha_fin}")
            logger.info(f"  - Estado: {estado}")
            logger.info(f"  - Duración: {duracion_minutos} min")
            logger.info(f"  - Temp Max: {max_temp}°C")
            
            # Buscar si ya existe en Supabase por fecha de inicio
            existing_response = client.table('eventos_temperatura')\
                .select('*')\
                .eq('camara_id', camera['id'])\
                .eq('fecha_inicio', fecha_inicio.isoformat())\
                .execute()
            
            if existing_response.data:
                # Actualizar evento existente
                supabase_event = existing_response.data[0]
                event_db_id = supabase_event['id']
                
                logger.info(f"  ✏️  Actualizando evento existente ID: {event_db_id}")
                
                update_data = {
                    'tipo': event_type,
                    'duracion_minutos': duracion_minutos,
                    'temp_max_c': float(max_temp),
                    'estado': estado
                }
                
                if fecha_fin:
                    update_data['fecha_fin'] = fecha_fin.isoformat()
                
                result = client.table('eventos_temperatura')\
                    .update(update_data)\
                    .eq('id', event_db_id)\
                    .execute()
                
                if result.data:
                    logger.info(f"  ✅ Evento actualizado correctamente")
                else:
                    logger.error(f"  ❌ Error al actualizar evento")
            else:
                # Crear nuevo evento
                logger.info(f"  ➕ Creando nuevo evento")
                
                insert_data = {
                    'camara_id': camera['id'],
                    'fecha_inicio': fecha_inicio.isoformat(),
                    'tipo': event_type,
                    'temp_max_c': float(max_temp),
                    'duracion_minutos': duracion_minutos,
                    'estado': estado
                }
                
                if fecha_fin:
                    insert_data['fecha_fin'] = fecha_fin.isoformat()
                
                result = client.table('eventos_temperatura')\
                    .insert(insert_data)\
                    .execute()
                
                if result.data:
                    logger.info(f"  ✅ Evento creado correctamente")
                else:
                    logger.error(f"  ❌ Error al crear evento")
        
        logger.info(f"\n🎉 Sincronización completada")
        
    except Exception as e:
        logger.error(f"Error al sincronizar eventos: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    sync_all_events_today()