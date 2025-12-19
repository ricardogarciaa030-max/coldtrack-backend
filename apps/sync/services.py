"""
Servicios de Sincronización

Sincroniza datos desde Firebase Realtime Database hacia Supabase PostgreSQL.

Funciones principales:
- sync_device_readings(): Sincroniza lecturas de un dispositivo
- sync_device_events(): Sincroniza eventos de un dispositivo
- generate_daily_summary(): Genera resumen diario de una cámara
- sync_all_devices(): Sincroniza todos los dispositivos
"""

import logging
from datetime import datetime, date, timedelta
from typing import Optional, List
from decimal import Decimal

from services.firebase_service import (
    get_live_status,
    get_daily_controls,
    get_firebase_events,
    get_all_devices
)
from services.supabase_service import (
    get_camera_by_firebase_path,
    insert_temperature_reading,
    insert_event,
    update_event_end,
    insert_daily_summary,
    get_open_events_for_camera
)

logger = logging.getLogger(__name__)


def sync_device_readings(device_id: str, target_date: Optional[date] = None) -> dict:
    """
    Sincroniza las lecturas de temperatura de un dispositivo desde /status/.
    
    Lee las lecturas del día desde Firebase /status/ y las inserta en Supabase.
    
    Args:
        device_id: ID del dispositivo en Firebase
        target_date: Fecha a sincronizar (por defecto hoy)
    
    Returns:
        Dict con estadísticas de la sincronización:
            - device_id: ID del dispositivo
            - lecturas_insertadas: Cantidad de lecturas insertadas
            - errores: Cantidad de errores
    """
    if target_date is None:
        target_date = date.today()
    
    logger.info(f"Sincronizando lecturas de {device_id} para {target_date}")
    
    # Buscar cámara en Supabase
    camera = get_camera_by_firebase_path(device_id)
    if not camera:
        logger.warning(f"Cámara no encontrada para device_id {device_id}")
        return {
            'device_id': device_id,
            'lecturas_insertadas': 0,
            'errores': 1,
            'error': 'Cámara no encontrada'
        }
    
    # Obtener lecturas del día desde Firebase /status/
    from services.firebase_service import get_device_status_readings
    status_readings = get_device_status_readings(device_id, target_date)
    
    lecturas_insertadas = 0
    errores = 0
    
    for reading in status_readings:
        try:
            # Convertir timestamp de segundos a datetime
            timestamp = datetime.fromtimestamp(reading['ts'])
            
            # Verificar si ya existe
            from services.supabase_service import get_supabase_client
            client = get_supabase_client(use_service_key=True)
            
            existing = client.table('lecturas_temperatura')\
                .select('id')\
                .eq('camara_id', camera['id'])\
                .eq('timestamp', timestamp.isoformat())\
                .execute()
            
            if existing.data and len(existing.data) > 0:
                # Ya existe, continuar
                continue
            
            # Insertar lectura en Supabase
            result = insert_temperature_reading(
                camara_id=camera['id'],
                timestamp=timestamp,
                temperatura_c=reading['temp'],
                origen='firebase:status'
            )
            
            if result:
                lecturas_insertadas += 1
            else:
                errores += 1
                
        except Exception as e:
            logger.error(f"Error al insertar lectura: {str(e)}")
            errores += 1
    
    logger.info(f"Sincronización completada: {lecturas_insertadas} lecturas, {errores} errores")
    
    return {
        'device_id': device_id,
        'lecturas_insertadas': lecturas_insertadas,
        'errores': errores
    }


def sync_device_events(device_id: str, target_date: Optional[date] = None) -> dict:
    """
    Sincroniza los eventos de temperatura de un dispositivo.
    
    Lee los eventos desde Firebase y los inserta/actualiza en Supabase.
    
    Args:
        device_id: ID del dispositivo en Firebase
        target_date: Fecha a sincronizar (por defecto hoy)
    
    Returns:
        Dict con estadísticas de la sincronización
    """
    if target_date is None:
        target_date = date.today()
    
    logger.info(f"Sincronizando eventos de {device_id} para {target_date}")
    
    # Buscar cámara en Supabase
    camera = get_camera_by_firebase_path(device_id)
    if not camera:
        logger.warning(f"Cámara no encontrada para device_id {device_id}")
        return {
            'device_id': device_id,
            'eventos_insertados': 0,
            'errores': 1,
            'error': 'Cámara no encontrada'
        }
    
    # Obtener eventos desde Firebase
    firebase_events = get_firebase_events(device_id, target_date)
    
    eventos_insertados = 0
    eventos_actualizados = 0
    errores = 0
    
    for fb_event in firebase_events:
        try:
            # Convertir timestamps de segundos a datetime
            fecha_inicio = datetime.fromtimestamp(fb_event['start_ts'])
            fecha_fin = None
            duracion_minutos = None
            
            if fb_event.get('ended') and fb_event.get('end_ts'):
                fecha_fin = datetime.fromtimestamp(fb_event['end_ts'])
                duracion_minutos = fb_event.get('duration_ms', 0) // 60000
            
            # Determinar estado
            estado = 'RESUELTO' if fb_event.get('ended') else 'EN_CURSO'
            
            # Insertar evento en Supabase
            result = insert_event(
                camara_id=camera['id'],
                fecha_inicio=fecha_inicio,
                tipo=fb_event['type'],
                temp_max_c=fb_event.get('max_temp', 0),
                fecha_fin=fecha_fin,
                duracion_minutos=duracion_minutos,
                estado=estado
            )
            
            if result:
                eventos_insertados += 1
            else:
                errores += 1
                
        except Exception as e:
            logger.error(f"Error al insertar evento: {str(e)}")
            errores += 1
    
    logger.info(f"Eventos sincronizados: {eventos_insertados} insertados, {errores} errores")
    
    return {
        'device_id': device_id,
        'eventos_insertados': eventos_insertados,
        'eventos_actualizados': eventos_actualizados,
        'errores': errores
    }


def generate_daily_summary(device_id: str, target_date: Optional[date] = None) -> dict:
    """
    Genera el resumen diario de una cámara.
    
    Calcula estadísticas del día y las guarda en resumen_diario_camara.
    
    Args:
        device_id: ID del dispositivo
        target_date: Fecha del resumen (por defecto hoy)
    
    Returns:
        Dict con el resumen generado
    """
    if target_date is None:
        target_date = date.today()
    
    logger.info(f"Generando resumen diario de {device_id} para {target_date}")
    
    # Buscar cámara
    camera = get_camera_by_firebase_path(device_id)
    if not camera:
        return {'error': 'Cámara no encontrada'}
    
    # Obtener controles del día
    controls = get_daily_controls(device_id, target_date)
    
    if not controls:
        logger.warning(f"No hay controles para generar resumen de {device_id}")
        return {'error': 'No hay datos'}
    
    # Calcular estadísticas
    temperaturas = [c['temp'] for c in controls]
    temp_min = min(temperaturas)
    temp_max = max(temperaturas)
    temp_promedio = sum(temperaturas) / len(temperaturas)
    
    # Contar eventos del día
    eventos = get_firebase_events(device_id, target_date)
    alertas_descongelamiento = sum(
        1 for e in eventos 
        if e['type'] in ['DESHIELO_N', 'DESHIELO_P']
    )
    fallas_detectadas = sum(
        1 for e in eventos 
        if e['type'] in ['FALLA', 'FALLA_EN_CURSO']
    )
    
    # Insertar resumen
    result = insert_daily_summary(
        fecha=target_date,
        camara_id=camera['id'],
        temp_min=temp_min,
        temp_max=temp_max,
        temp_promedio=temp_promedio,
        total_lecturas=len(controls),
        alertas_descongelamiento=alertas_descongelamiento,
        fallas_detectadas=fallas_detectadas
    )
    
    if result:
        logger.info(f"Resumen diario generado para {device_id}")
        return result
    else:
        return {'error': 'Error al generar resumen'}


def sync_all_devices(target_date: Optional[date] = None) -> dict:
    """
    Sincroniza todos los dispositivos registrados en Firebase.
    
    Args:
        target_date: Fecha a sincronizar (por defecto hoy)
    
    Returns:
        Dict con estadísticas globales de la sincronización
    """
    if target_date is None:
        target_date = date.today()
    
    logger.info(f"Iniciando sincronización global para {target_date}")
    
    # Obtener todos los dispositivos
    devices = get_all_devices()
    
    total_lecturas = 0
    total_eventos = 0
    total_resumenes = 0
    errores = 0
    
    for device_id in devices:
        try:
            # Sincronizar lecturas
            result_lecturas = sync_device_readings(device_id, target_date)
            total_lecturas += result_lecturas.get('lecturas_insertadas', 0)
            errores += result_lecturas.get('errores', 0)
            
            # Sincronizar eventos
            result_eventos = sync_device_events(device_id, target_date)
            total_eventos += result_eventos.get('eventos_insertados', 0)
            errores += result_eventos.get('errores', 0)
            
            # Generar resumen diario
            result_resumen = generate_daily_summary(device_id, target_date)
            if not result_resumen.get('error'):
                total_resumenes += 1
            
        except Exception as e:
            logger.error(f"Error al sincronizar dispositivo {device_id}: {str(e)}")
            errores += 1
    
    logger.info(f"Sincronización global completada: {len(devices)} dispositivos procesados")
    
    return {
        'fecha': target_date.isoformat(),
        'dispositivos_procesados': len(devices),
        'total_lecturas': total_lecturas,
        'total_eventos': total_eventos,
        'total_resumenes': total_resumenes,
        'errores': errores
    }
