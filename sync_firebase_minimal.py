"""
Sistema de sincronización optimizado con firebase_event_id
Solo usa los campos que existen en Supabase
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
from datetime import datetime, date
import logging
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def sync_events_with_firebase_id():
    """
    Sincronizar eventos usando firebase_event_id para evitar duplicados
    """
    try:
        initialize_firebase()
        client = get_supabase_client(use_service_key=True)
        
        # Obtener datos de eventos de Firebase
        events_ref = db.reference('eventos')
        events_data = events_ref.get()
        
        if not events_data:
            logger.info("No hay datos de eventos en Firebase")
            return
        
        logger.info(f"🔥 Procesando eventos con firebase_event_id...")
        
        eventos_procesados = 0
        eventos_nuevos = 0
        eventos_actualizados = 0
        
        for device_id, device_events in events_data.items():
            # Buscar cámara en Supabase
            camera = get_camera_by_firebase_path(device_id)
            if not camera:
                logger.warning(f"Cámara no encontrada: {device_id}")
                continue
            
            # Procesar por año/mes/día
            for year, year_data in device_events.items():
                if not isinstance(year_data, dict):
                    continue
                    
                for month, month_data in year_data.items():
                    if not isinstance(month_data, dict):
                        continue
                        
                    for day, day_data in month_data.items():
                        if not isinstance(day_data, dict):
                            continue
                        
                        # Procesar cada evento del día
                        for event_id, event_data in day_data.items():
                            if not isinstance(event_data, dict):
                                continue
                            
                            try:
                                resultado = sync_single_event_minimal(client, camera, event_id, event_data)
                                eventos_procesados += 1
                                
                                if resultado == 'nuevo':
                                    eventos_nuevos += 1
                                elif resultado == 'actualizado':
                                    eventos_actualizados += 1
                                    
                            except Exception as e:
                                logger.error(f"Error procesando evento {event_id}: {str(e)}")
                                continue
        
        logger.info(f"🎉 Sincronización completada:")
        logger.info(f"  📊 Total procesados: {eventos_procesados}")
        logger.info(f"  🆕 Nuevos: {eventos_nuevos}")
        logger.info(f"  ✅ Actualizados: {eventos_actualizados}")
        
    except Exception as e:
        logger.error(f"Error en sincronización de eventos: {str(e)}")
        import traceback
        traceback.print_exc()


def sync_single_event_minimal(client, camera, firebase_event_id, event_data):
    """
    Sincronizar un evento individual usando firebase_event_id
    """
    try:
        # Extraer datos de Firebase
        start_ts = event_data.get('start_ts')
        end_ts = event_data.get('end_ts')
        duration_ms = event_data.get('duration_ms', 0)
        max_temp = event_data.get('max_temp', 0)
        event_type = event_data.get('type', 'UNKNOWN')
        
        if not start_ts:
            logger.warning(f"Evento sin start_ts: {firebase_event_id}")
            return None
        
        # Convertir timestamps
        fecha_inicio = datetime.fromtimestamp(start_ts)
        fecha_fin = None
        if end_ts:
            fecha_fin = datetime.fromtimestamp(end_ts)
        
        # Calcular duración en minutos
        duracion_minutos = duration_ms // 60000 if duration_ms else 0
        
        # Determinar estado del evento
        estado = 'RESUELTO' if end_ts else 'EN_CURSO'
        
        # 🎯 BUSCAR POR firebase_event_id (¡esto es lo nuevo!)
        existing_response = client.table('eventos_temperatura')\
            .select('*')\
            .eq('firebase_event_id', firebase_event_id)\
            .execute()
        
        if existing_response.data:
            # ✅ Actualizar evento existente usando firebase_event_id
            event_supabase_id = existing_response.data[0]['id']
            
            update_data = {
                'fecha_fin': fecha_fin.isoformat() if fecha_fin else None,
                'duracion_minutos': duracion_minutos,
                'temp_max_c': float(max_temp),
                'estado': estado
            }
            
            result = client.table('eventos_temperatura')\
                .update(update_data)\
                .eq('id', event_supabase_id)\
                .execute()
            
            if result.data:
                status_emoji = "🔴" if estado == 'EN_CURSO' else "✅"
                logger.info(f"{status_emoji} Actualizado: {firebase_event_id} - {event_type} - {estado}")
                return 'actualizado'
            else:
                logger.error(f"❌ Error actualizando: {firebase_event_id}")
                return None
        
        else:
            # 🆕 Crear nuevo evento con firebase_event_id
            insert_data = {
                'camara_id': camera['id'],
                'firebase_event_id': firebase_event_id,  # 🎯 Esto es lo importante
                'fecha_inicio': fecha_inicio.isoformat(),
                'fecha_fin': fecha_fin.isoformat() if fecha_fin else None,
                'tipo': event_type,
                'temp_max_c': float(max_temp),
                'duracion_minutos': duracion_minutos,
                'estado': estado
            }
            
            result = client.table('eventos_temperatura')\
                .insert(insert_data)\
                .execute()
            
            if result.data:
                status_emoji = "🔴" if estado == 'EN_CURSO' else "🆕"
                logger.info(f"{status_emoji} Nuevo: {firebase_event_id} - {event_type} - {estado}")
                return 'nuevo'
            else:
                logger.error(f"❌ Error creando: {firebase_event_id}")
                return None
    
    except Exception as e:
        logger.error(f"Error en sync_single_event_minimal: {str(e)}")
        return None


def sync_status_minimal():
    """
    Sincronizar temperaturas (sin cambios, ya funciona bien)
    """
    try:
        initialize_firebase()
        client = get_supabase_client(use_service_key=True)
        
        # Obtener datos de status de Firebase
        status_ref = db.reference('status')
        status_data = status_ref.get()
        
        if not status_data:
            logger.info("No hay datos de status en Firebase")
            return
        
        logger.info(f"📊 Procesando temperaturas...")
        
        lecturas_procesadas = 0
        
        for device_id, device_data in status_data.items():
            # Buscar cámara en Supabase
            camera = get_camera_by_firebase_path(device_id)
            if not camera:
                logger.warning(f"Cámara no encontrada: {device_id}")
                continue
            
            # Procesar cada timestamp
            for timestamp_key, reading_data in device_data.items():
                if not isinstance(reading_data, dict):
                    continue
                
                # Saltar entradas que no son timestamps válidos
                if timestamp_key == 'live' or not timestamp_key.isdigit():
                    continue
                
                try:
                    # Extraer datos
                    timestamp_unix = int(timestamp_key)
                    fecha_lectura = datetime.fromtimestamp(timestamp_unix)
                    temperatura = float(reading_data.get('temp', 0))
                    
                    # Verificar si ya existe esta lectura
                    existing_response = client.table('lecturas_temperatura')\
                        .select('id')\
                        .eq('camara_id', camera['id'])\
                        .eq('timestamp', fecha_lectura.isoformat())\
                        .execute()
                    
                    if not existing_response.data:
                        # Crear nueva lectura
                        insert_data = {
                            'camara_id': camera['id'],
                            'timestamp': fecha_lectura.isoformat(),
                            'temperatura_c': temperatura,
                            'origen': 'firebase_sync'
                        }
                        
                        result = client.table('lecturas_temperatura')\
                            .insert(insert_data)\
                            .execute()
                        
                        if result.data:
                            lecturas_procesadas += 1
                
                except Exception as e:
                    logger.error(f"Error procesando lectura {timestamp_key}: {str(e)}")
                    continue
        
        logger.info(f"📊 Temperaturas: {lecturas_procesadas} nuevas lecturas")
        
    except Exception as e:
        logger.error(f"Error en sincronización de temperaturas: {str(e)}")


def sync_all_minimal():
    """Sincronizar todo con el nuevo sistema optimizado"""
    logger.info("🚀 Iniciando sincronización optimizada...")
    
    # Sincronizar temperaturas
    sync_status_minimal()
    
    # Sincronizar eventos con firebase_event_id
    sync_events_with_firebase_id()
    
    logger.info("🎉 Sincronización optimizada completada")


def monitor_minimal():
    """Monitor continuo optimizado"""
    logger.info("🔄 Iniciando monitor optimizado...")
    logger.info("Presiona Ctrl+C para detener")
    
    try:
        while True:
            sync_all_minimal()
            logger.info("⏰ Esperando 30 segundos...")
            time.sleep(30)
            
    except KeyboardInterrupt:
        logger.info("🛑 Monitor detenido por el usuario")
    except Exception as e:
        logger.error(f"Error en monitor: {str(e)}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "monitor":
            monitor_minimal()
        elif sys.argv[1] == "events":
            sync_events_with_firebase_id()
        elif sys.argv[1] == "status":
            sync_status_minimal()
        else:
            print("Uso: python sync_firebase_minimal.py [monitor|events|status]")
    else:
        sync_all_minimal()