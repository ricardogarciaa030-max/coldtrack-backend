"""
Servicio de Sincronización Integrado en Django

Este módulo maneja la sincronización automática entre Firebase y Supabase
como parte del backend Django.
"""

import time
import logging
from datetime import datetime, date
from firebase_admin import db
from services.firebase_service import initialize_firebase
from services.supabase_service import (
    get_camera_by_firebase_path,
    insert_temperature_reading,
    insert_event,
    get_supabase_client
)

logger = logging.getLogger(__name__)

# Diccionario para rastrear eventos procesados
processed_events = {}

def on_event_change(device_id, event_id, data):
    """Callback cuando cambia un evento en Firebase"""
    try:
        if not data or not isinstance(data, dict):
            return
        
        # Evitar procesar el mismo evento múltiples veces
        event_key = f"{device_id}:{event_id}"
        if event_key in processed_events and processed_events[event_key] == data.get('ended'):
            return
        
        logger.info(f"🔄 Evento detectado: {device_id} - {event_id} - Tipo: {data.get('type')}")
        
        # Buscar cámara
        camera = get_camera_by_firebase_path(device_id)
        if not camera:
            logger.warning(f"⚠️ Cámara no encontrada: {device_id}")
            return
        
        # Usar la función que maneja firebase_event_id correctamente
        client = get_supabase_client(use_service_key=True)
        resultado = sync_single_event_with_firebase_id(client, camera, event_id, data)
        
        if resultado:
            processed_events[event_key] = data.get('ended')
            logger.info(f"✅ Evento procesado: {camera['nombre']} - {data['type']} - {resultado}")
            
    except Exception as e:
        logger.error(f"❌ Error en sincronización de evento: {str(e)}")

def on_status_change(device_id, timestamp_key, data):
    """Callback cuando cambia el status (lectura en tiempo real)"""
    try:
        if not data or timestamp_key == 'live':
            return
        
        # Buscar cámara
        camera = get_camera_by_firebase_path(device_id)
        if not camera:
            return
        
        # Convertir timestamp
        timestamp = datetime.fromtimestamp(int(timestamp_key))
        
        # Verificar si la lectura ya existe
        client = get_supabase_client(use_service_key=True)
        existing = client.table('lecturas_temperatura')\
            .select('id')\
            .eq('camara_id', camera['id'])\
            .eq('timestamp', timestamp.isoformat())\
            .execute()
        
        if existing.data and len(existing.data) > 0:
            return
        
        # Insertar lectura
        result = insert_temperature_reading(
            camara_id=camera['id'],
            timestamp=timestamp,
            temperatura_c=data['temp'],
            origen='firebase:status'
        )
        
        if result:
            logger.info(f"📊 Lectura sincronizada: {camera['nombre']} - {data['temp']}°C")
            
    except Exception as e:
        logger.error(f"❌ Error en sincronización de lectura: {str(e)}")

def sync_events_periodic():
    """Sincronización periódica de eventos usando firebase_event_id"""
    try:
        client = get_supabase_client(use_service_key=True)
        
        # Obtener datos de eventos de Firebase
        events_ref = db.reference('eventos')
        events_data = events_ref.get()
        
        if not events_data:
            return
        
        eventos_procesados = 0
        
        for device_id, device_events in events_data.items():
            camera = get_camera_by_firebase_path(device_id)
            if not camera:
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
                                sync_single_event_with_firebase_id(client, camera, event_id, event_data)
                                eventos_procesados += 1
                            except Exception as e:
                                logger.error(f"Error procesando evento {event_id}: {str(e)}")
                                continue
        
        if eventos_procesados > 0:
            logger.info(f"🔄 Sincronización periódica: {eventos_procesados} eventos procesados")
        
    except Exception as e:
        logger.error(f"Error en sincronización periódica: {str(e)}")

def sync_single_event_with_firebase_id(client, camera, firebase_event_id, event_data):
    """Sincronizar un evento individual usando firebase_event_id"""
    try:
        start_ts = event_data.get('start_ts')
        end_ts = event_data.get('end_ts')
        duration_ms = event_data.get('duration_ms', 0)
        max_temp = event_data.get('max_temp', 0)
        event_type = event_data.get('type', 'UNKNOWN')
        
        if not start_ts:
            return None
        
        fecha_inicio = datetime.fromtimestamp(start_ts)
        fecha_fin = None
        if end_ts:
            fecha_fin = datetime.fromtimestamp(end_ts)
        
        duracion_minutos = duration_ms // 60000 if duration_ms else 0
        estado_firebase = 'RESUELTO' if end_ts else 'EN_CURSO'
        
        # Buscar por firebase_event_id
        existing_response = client.table('eventos_temperatura')\
            .select('*')\
            .eq('firebase_event_id', firebase_event_id)\
            .execute()
        
        if existing_response.data:
            # Actualizar evento existente
            existing_event = existing_response.data[0]
            event_supabase_id = existing_event['id']
            estado_actual = existing_event['estado']
            
            # 🔧 LÓGICA ESPECIAL: Si el evento está marcado manualmente como EN_CURSO
            # y es una FALLA_EN_CURSO, NO lo actualices automáticamente a RESUELTO
            if (estado_actual == 'EN_CURSO' and 
                event_type == 'FALLA_EN_CURSO' and 
                estado_firebase == 'RESUELTO'):
                
                # Solo actualizar temperatura máxima, pero mantener EN_CURSO
                update_data = {
                    'temp_max_c': float(max_temp)
                }
                logger.info(f"🔒 Manteniendo evento EN_CURSO (corrección manual): {firebase_event_id}")
                
            else:
                # Actualización normal
                update_data = {
                    'fecha_fin': fecha_fin.isoformat() if fecha_fin else None,
                    'duracion_minutos': duracion_minutos,
                    'temp_max_c': float(max_temp),
                    'estado': estado_firebase
                }
                logger.info(f"📝 Actualizando evento normal: {firebase_event_id} - {estado_actual} → {estado_firebase}")
            
            result = client.table('eventos_temperatura')\
                .update(update_data)\
                .eq('id', event_supabase_id)\
                .execute()
            
            return 'actualizado' if result.data else None
        
        else:
            # Crear nuevo evento
            insert_data = {
                'camara_id': camera['id'],
                'firebase_event_id': firebase_event_id,
                'fecha_inicio': fecha_inicio.isoformat(),
                'fecha_fin': fecha_fin.isoformat() if fecha_fin else None,
                'tipo': event_type,
                'temp_max_c': float(max_temp),
                'duracion_minutos': duracion_minutos,
                'estado': estado_firebase,
                'created_at': fecha_inicio.isoformat()  # 🔧 Usar fecha_inicio como created_at
            }
            
            result = client.table('eventos_temperatura')\
                .insert(insert_data)\
                .execute()
            
            if result.data:
                logger.info(f"🆕 Nuevo evento: {firebase_event_id} - {event_type} - {estado_firebase}")
                return 'nuevo'
            
    except Exception as e:
        logger.error(f"Error en sync_single_event_with_firebase_id: {str(e)}")
        return None

def start_sync_service():
    """
    Inicia el servicio de sincronización completo:
    - Listeners en tiempo real para cambios inmediatos
    - Sincronización periódica cada 30 segundos para garantizar consistencia
    """
    try:
        logger.info("🚀 Iniciando servicio de sincronización Firebase → Supabase")
        
        # Inicializar Firebase
        initialize_firebase()
        
        # Obtener dispositivos
        devices_ref = db.reference('/status')
        devices = devices_ref.get()
        
        if not devices:
            logger.warning("⚠️ No se encontraron dispositivos en Firebase")
            return
        
        logger.info(f"📱 Dispositivos encontrados: {list(devices.keys())}")
        
        # Configurar listeners para cada dispositivo (tiempo real)
        for device_id in devices.keys():
            logger.info(f"🔧 Configurando listeners para: {device_id}")
            
            # Listener para eventos del día actual
            today = date.today()
            year = today.year
            month = str(today.month).zfill(2)
            day = str(today.day).zfill(2)
            
            events_path = f'/eventos/{device_id}/{year}/{month}/{day}'
            events_ref = db.reference(events_path)
            
            def make_event_callback(dev_id):
                def callback(event):
                    if event.data:
                        for evt_id, data in event.data.items():
                            on_event_change(dev_id, evt_id, data)
                return callback
            
            events_ref.listen(make_event_callback(device_id))
            logger.info(f"  ✓ Eventos tiempo real: {events_path}")
            
            # Listener para status en tiempo real
            status_path = f'/status/{device_id}/{year}/{month}/{day}'
            status_ref = db.reference(status_path)
            
            def make_status_callback(dev_id):
                def callback(event):
                    if event.data:
                        for ts_key, data in event.data.items():
                            on_status_change(dev_id, ts_key, data)
                return callback
            
            status_ref.listen(make_status_callback(device_id))
            logger.info(f"  ✓ Status tiempo real: {status_path}")
        
        logger.info("✅ Listeners en tiempo real configurados")
        logger.info("🔄 Iniciando sincronización periódica cada 30 segundos...")
        
        # Bucle principal con sincronización periódica
        while True:
            time.sleep(30)  # Esperar 30 segundos
            
            # Ejecutar sincronización periódica
            sync_events_periodic()
            
    except Exception as e:
        logger.error(f"💥 Error fatal en servicio de sincronización: {str(e)}")
        import traceback
        traceback.print_exc()