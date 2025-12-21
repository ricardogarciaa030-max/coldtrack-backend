"""
Servicio de Sincronización Integrado en Django

Este módulo maneja la sincronización automática entre Firebase y Supabase
como parte del backend Django.
"""

import time
import logging
import os
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

# Variable global para controlar el estado del servicio
sync_service_running = False

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

def sync_users_periodic():
    """Sincronización periódica de usuarios Firebase Auth → Supabase"""
    try:
        import firebase_admin
        from firebase_admin import auth
        from django.conf import settings
        import requests
        
        # Verificar si Firebase ya está inicializado
        try:
            firebase_admin.get_app()
        except ValueError:
            logger.warning("Firebase no inicializado para sincronización de usuarios")
            return
        
        config = settings.SUPABASE_CONFIG
        headers = {
            'apikey': config['service_key'],
            'Authorization': f'Bearer {config["service_key"]}',
            'Content-Type': 'application/json',
            'Prefer': 'return=representation'
        }
        
        # Obtener usuarios de Firebase Auth
        page = auth.list_users()
        users_synced = 0
        users_updated = 0
        
        while page:
            for user in page.users:
                try:
                    # Verificar si el usuario ya existe en Supabase
                    check_url = f'{config["url"]}/rest/v1/usuarios?firebase_uid=eq.{user.uid}'
                    check_response = requests.get(check_url, headers=headers)
                    
                    if check_response.status_code == 200:
                        existing_users = check_response.json()
                        
                        if len(existing_users) > 0:
                            # Usuario existe, verificar si necesita actualización
                            existing_user = existing_users[0]
                            needs_update = False
                            update_data = {}
                            
                            # Verificar email
                            if existing_user.get('email') != user.email:
                                update_data['email'] = user.email
                                needs_update = True
                            
                            # Verificar nombre
                            display_name = user.display_name or user.email.split('@')[0]
                            if existing_user.get('nombre') != display_name:
                                update_data['nombre'] = display_name
                                needs_update = True
                            
                            # Verificar estado activo
                            is_active = not user.disabled
                            if existing_user.get('activo') != is_active:
                                update_data['activo'] = is_active
                                needs_update = True
                            
                            if needs_update:
                                # Actualizar usuario existente
                                update_url = f'{config["url"]}/rest/v1/usuarios?firebase_uid=eq.{user.uid}'
                                update_response = requests.patch(update_url, json=update_data, headers=headers)
                                
                                if update_response.status_code in [200, 204]:
                                    users_updated += 1
                                    logger.info(f"👤 Usuario actualizado: {user.email}")
                        else:
                            # Usuario no existe, crearlo
                            user_data = {
                                'firebase_uid': user.uid,
                                'email': user.email,
                                'nombre': user.display_name or user.email.split('@')[0],
                                'rol': 'ADMIN',  # Por defecto ADMIN
                                'activo': not user.disabled,
                                'sucursal_id': 1  # Sucursal por defecto
                            }
                            
                            create_url = f'{config["url"]}/rest/v1/usuarios'
                            create_response = requests.post(create_url, json=user_data, headers=headers)
                            
                            if create_response.status_code in [200, 201]:
                                users_synced += 1
                                logger.info(f"👤 Usuario sincronizado: {user.email}")
                
                except Exception as user_error:
                    logger.error(f"Error procesando usuario {user.email}: {str(user_error)}")
                    continue
            
            # Siguiente página
            page = page.get_next_page()
        
        if users_synced > 0 or users_updated > 0:
            logger.info(f"👥 Sincronización de usuarios: {users_synced} nuevos, {users_updated} actualizados")
        
    except Exception as e:
        logger.error(f"Error en sincronización de usuarios: {str(e)}")

def sync_temperature_readings_periodic():
    """Sincronización periódica de lecturas de temperatura"""
    try:
        client = get_supabase_client(use_service_key=True)
        
        # Obtener datos de status de Firebase
        status_ref = db.reference('status')
        status_data = status_ref.get()
        
        if not status_data:
            return
        
        lecturas_procesadas = 0
        
        for device_id, device_status in status_data.items():
            camera = get_camera_by_firebase_path(device_id)
            if not camera:
                continue
            
            # Procesar por año/mes/día
            for year, year_data in device_status.items():
                if not isinstance(year_data, dict) or year == 'live':
                    continue
                    
                for month, month_data in year_data.items():
                    if not isinstance(month_data, dict):
                        continue
                        
                    for day, day_data in month_data.items():
                        if not isinstance(day_data, dict):
                            continue
                        
                        # Procesar cada lectura del día
                        for timestamp_key, reading_data in day_data.items():
                            if not isinstance(reading_data, dict) or timestamp_key == 'live':
                                continue
                            
                            try:
                                # Convertir timestamp
                                timestamp = datetime.fromtimestamp(int(timestamp_key))
                                
                                # Verificar si la lectura ya existe
                                existing = client.table('lecturas_temperatura')\
                                    .select('id')\
                                    .eq('camara_id', camera['id'])\
                                    .eq('timestamp', timestamp.isoformat())\
                                    .execute()
                                
                                if existing.data and len(existing.data) > 0:
                                    continue  # Ya existe
                                
                                # Insertar nueva lectura
                                lectura_data = {
                                    'camara_id': camera['id'],
                                    'timestamp': timestamp.isoformat(),
                                    'temperatura_c': float(reading_data.get('temp', 0)),
                                    'estado': reading_data.get('state', 'NORMAL'),
                                    'origen': 'firebase:status'
                                }
                                
                                result = client.table('lecturas_temperatura')\
                                    .insert(lectura_data)\
                                    .execute()
                                
                                if result.data:
                                    lecturas_procesadas += 1
                                    logger.info(f"📊 Lectura sincronizada: {camera['nombre']} - {reading_data.get('temp')}°C - {timestamp.strftime('%H:%M:%S')}")
                                
                            except Exception as e:
                                logger.error(f"Error procesando lectura {timestamp_key}: {str(e)}")
                                continue
        
        if lecturas_procesadas > 0:
            logger.info(f"📊 Sincronización de lecturas: {lecturas_procesadas} lecturas procesadas")
        
    except Exception as e:
        logger.error(f"Error en sincronización de lecturas: {str(e)}")

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
        
        # 🔧 LÓGICA ESPECIAL PARA EVENTOS EN CURSO:
        # Los eventos que terminan en "_EN_CURSO" siempre deben mantenerse EN_CURSO
        # hasta que Firebase indique explícitamente que terminaron
        if event_type.endswith('_EN_CURSO'):
            estado_firebase = 'EN_CURSO'
        else:
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
            
            # 🔧 LÓGICA ESPECIAL: Si el evento está EN_CURSO en Supabase
            # y el tipo termina en "_EN_CURSO", mantenerlo EN_CURSO
            if estado_actual == 'EN_CURSO' and event_type.endswith('_EN_CURSO'):
                # Solo actualizar duración y temperatura, mantener EN_CURSO
                update_data = {
                    'duracion_minutos': duracion_minutos,
                    'temp_max_c': float(max_temp)
                }
                logger.info(f"🔒 Manteniendo evento EN_CURSO: {firebase_event_id} - {event_type}")
                
            else:
                # Actualización normal
                update_data = {
                    'fecha_fin': fecha_fin.isoformat() if fecha_fin else None,
                    'duracion_minutos': duracion_minutos,
                    'temp_max_c': float(max_temp),
                    'estado': estado_firebase
                }
                logger.info(f"📝 Actualizando evento: {firebase_event_id} - {estado_actual} → {estado_firebase}")
            
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
    global sync_service_running
    
    if sync_service_running:
        logger.warning("🔄 Servicio de sincronización ya está ejecutándose")
        return
    
    sync_service_running = True
    
    try:
        logger.info("🚀 Iniciando servicio de sincronización Firebase → Supabase")
        logger.info(f"🌍 Entorno: {'Desarrollo' if os.environ.get('DEBUG', 'False') == 'True' else 'Producción'}")
        
        # Inicializar Firebase
        if not initialize_firebase():
            logger.error("❌ No se pudo inicializar Firebase")
            sync_service_running = False
            return
        
        logger.info("✅ Firebase inicializado correctamente")
        
        # Obtener dispositivos
        devices_ref = db.reference('/status')
        devices = devices_ref.get()
        
        if not devices:
            logger.warning("⚠️ No se encontraron dispositivos en Firebase")
            # Continuar con sincronización periódica aunque no haya dispositivos
        else:
            logger.info(f"📱 Dispositivos encontrados: {list(devices.keys())}")
            
            # En producción, solo usar sincronización periódica (más estable)
            # Los listeners en tiempo real pueden causar problemas en Render
            if os.environ.get('DEBUG', 'False') == 'True':
                # Solo en desarrollo usar listeners
                logger.info("🔧 Configurando listeners en tiempo real (desarrollo)")
                setup_realtime_listeners(devices)
            else:
                logger.info("🔧 Modo producción: solo sincronización periódica")
        
        logger.info("🔄 Iniciando sincronización periódica cada 30 segundos...")
        
        # Contador para sincronización de usuarios (cada 10 minutos = 20 ciclos de 30s)
        user_sync_counter = 0
        cycle_count = 0
        
        # Bucle principal con sincronización periódica
        while sync_service_running:
            try:
                time.sleep(30)  # Esperar 30 segundos
                cycle_count += 1
                
                logger.info(f"🔄 Ciclo de sincronización #{cycle_count} - {datetime.now().strftime('%H:%M:%S')}")
                
                # Ejecutar sincronización periódica de eventos
                sync_events_periodic()
                
                # Ejecutar sincronización periódica de lecturas de temperatura
                sync_temperature_readings_periodic()
                
                # Sincronizar usuarios cada 10 minutos (20 ciclos)
                user_sync_counter += 1
                if user_sync_counter >= 20:  # 20 * 30 segundos = 10 minutos
                    sync_users_periodic()
                    user_sync_counter = 0
                
                logger.info(f"✅ Ciclo #{cycle_count} completado")
                
            except Exception as cycle_error:
                logger.error(f"❌ Error en ciclo de sincronización #{cycle_count}: {str(cycle_error)}")
                # Continuar con el siguiente ciclo
                continue
            
    except Exception as e:
        logger.error(f"💥 Error fatal en servicio de sincronización: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        sync_service_running = False
        logger.info("🛑 Servicio de sincronización detenido")


def setup_realtime_listeners(devices):
    """Configurar listeners en tiempo real (solo para desarrollo)"""
    import os
    
    for device_id in devices.keys():
        logger.info(f"🔧 Configurando listeners para: {device_id}")
        
        try:
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
            
        except Exception as listener_error:
            logger.error(f"❌ Error configurando listeners para {device_id}: {str(listener_error)}")
            continue


def stop_sync_service():
    """Detener el servicio de sincronización"""
    global sync_service_running
    sync_service_running = False
    logger.info("🛑 Solicitando detención del servicio de sincronización")


def is_sync_service_running():
    """Verificar si el servicio está ejecutándose"""
    return sync_service_running