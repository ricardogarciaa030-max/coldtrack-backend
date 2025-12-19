"""
Sistema de sincronización para eventos en curso (FALLA_EN_CURSO)
Maneja eventos que se actualizan continuamente hasta que se resuelven
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
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def sync_live_event():
    """Sincronizar evento en curso desde Firebase"""
    try:
        # Inicializar Firebase
        initialize_firebase()
        
        # Obtener datos del evento actual
        device_id = 'camara1'
        # Buscar el evento EN_CURSO en la estructura correcta
        events_ref = db.reference(f'eventos/{device_id}/2025/12/09')
        events_data = events_ref.get()
        
        event_data = None
        if events_data:
            # Buscar el evento que no ha terminado (ended: False)
            for event_id, data in events_data.items():
                if isinstance(data, dict) and not data.get('ended', True):
                    event_data = data
                    logger.info(f"Evento EN_CURSO encontrado: {event_id}")
                    break
        
        if not event_data:
            logger.info("No hay evento EN_CURSO activo")
            return
        
        logger.info(f"Evento encontrado: {event_data}")
        
        # Buscar cámara en Supabase
        camera = get_camera_by_firebase_path(device_id)
        if not camera:
            logger.error(f"Cámara no encontrada: {device_id}")
            return
        
        # Extraer datos del evento
        start_ts = event_data.get('start_ts')
        end_ts = event_data.get('end_ts')
        duration_ms = event_data.get('duration_ms', 0)
        max_temp = event_data.get('max_temp', 0)
        event_type = event_data.get('type', 'FALLA_EN_CURSO')
        ended = event_data.get('ended', False)
        
        if not start_ts:
            logger.error("No se encontró start_ts en el evento")
            return
        
        # Convertir timestamps
        fecha_inicio = datetime.fromtimestamp(start_ts)
        fecha_fin = None
        duracion_minutos = duration_ms // 60000 if duration_ms else 0
        estado = 'EN_CURSO'
        
        if ended and end_ts:
            fecha_fin = datetime.fromtimestamp(end_ts)
            estado = 'RESUELTO'
        
        logger.info(f"Procesando evento:")
        logger.info(f"  - Tipo: {event_type}")
        logger.info(f"  - Inicio: {fecha_inicio}")
        logger.info(f"  - Duración: {duracion_minutos} minutos")
        logger.info(f"  - Estado: {estado}")
        logger.info(f"  - Temp Max: {max_temp}°C")
        logger.info(f"  - Terminado: {ended}")
        
        # Conectar a Supabase
        client = get_supabase_client(use_service_key=True)
        
        # Buscar si ya existe un evento EN_CURSO para esta cámara
        existing_response = client.table('eventos_temperatura')\
            .select('*')\
            .eq('camara_id', camera['id'])\
            .eq('tipo', event_type)\
            .eq('estado', 'EN_CURSO')\
            .execute()
        
        if existing_response.data:
            # Actualizar evento existente
            event_id = existing_response.data[0]['id']
            logger.info(f"Actualizando evento EN_CURSO existente ID: {event_id}")
            
            update_data = {
                'duracion_minutos': duracion_minutos,
                'temp_max_c': float(max_temp)
            }
            
            # Si el evento terminó, actualizar estado y fecha_fin
            if ended and fecha_fin:
                update_data.update({
                    'fecha_fin': fecha_fin.isoformat(),
                    'estado': 'RESUELTO'
                })
                logger.info("🔴 Evento RESUELTO - Cerrando falla")
            else:
                logger.info("🟡 Evento EN_CURSO - Actualizando duración")
            
            result = client.table('eventos_temperatura')\
                .update(update_data)\
                .eq('id', event_id)\
                .execute()
            
            if result.data:
                logger.info("✅ Evento actualizado correctamente")
                return result.data[0]
            else:
                logger.error("❌ Error al actualizar evento")
                
        else:
            # Crear nuevo evento EN_CURSO
            logger.info("🔴 Creando nuevo evento FALLA_EN_CURSO")
            
            insert_data = {
                'camara_id': camera['id'],
                'fecha_inicio': fecha_inicio.isoformat(),
                'tipo': event_type,
                'temp_max_c': float(max_temp),
                'duracion_minutos': duracion_minutos,
                'estado': estado
            }
            
            if ended and fecha_fin:
                insert_data.update({
                    'fecha_fin': fecha_fin.isoformat(),
                    'estado': 'RESUELTO'
                })
            
            result = client.table('eventos_temperatura')\
                .insert(insert_data)\
                .execute()
            
            if result.data:
                logger.info("✅ Evento creado correctamente")
                return result.data[0]
            else:
                logger.error("❌ Error al crear evento")
        
    except Exception as e:
        logger.error(f"Error al sincronizar evento: {str(e)}")
        import traceback
        traceback.print_exc()

def monitor_live_events():
    """Monitor continuo de eventos en curso"""
    logger.info("🔄 Iniciando monitor de eventos en curso...")
    logger.info("Presiona Ctrl+C para detener")
    
    try:
        while True:
            sync_live_event()
            time.sleep(30)  # Verificar cada 30 segundos
            
    except KeyboardInterrupt:
        logger.info("🛑 Monitor detenido por el usuario")
    except Exception as e:
        logger.error(f"Error en monitor: {str(e)}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "monitor":
        monitor_live_events()
    else:
        sync_live_event()