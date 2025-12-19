"""
Firebase Service

Este módulo centraliza todas las interacciones con Firebase Realtime Database.
Proporciona funciones para leer datos de temperatura, controles y eventos.

Funciones principales:
- initialize_firebase(): Inicializa Firebase Admin SDK
- get_live_status(device_id): Obtiene el estado en vivo de un dispositivo
- get_daily_controls(device_id, date): Obtiene los controles del día
- get_firebase_events(device_id, date): Obtiene eventos de un día específico
- get_all_devices(): Lista todos los dispositivos registrados
"""

import firebase_admin
from firebase_admin import credentials, db
from django.conf import settings
import logging
from datetime import datetime, date
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# Variable global para mantener la instancia de Firebase
_firebase_initialized = False


def initialize_firebase():
    """
    Inicializa Firebase Admin SDK con las credenciales del proyecto.
    
    Esta función debe ser llamada antes de usar cualquier otra función
    de este módulo. Es seguro llamarla múltiples veces.
    
    Returns:
        bool: True si la inicialización fue exitosa
    
    Raises:
        ValueError: Si faltan credenciales de Firebase
    """
    global _firebase_initialized
    
    if _firebase_initialized:
        return True
    
    try:
        # Intentar usar archivo de credenciales si existe
        creds_path = getattr(settings, 'FIREBASE_CREDENTIALS_PATH', None)
        if creds_path:
            import os
            full_path = os.path.join(settings.BASE_DIR, creds_path)
            if os.path.exists(full_path):
                cred = credentials.Certificate(full_path)
                firebase_admin.initialize_app(cred, {
                    'databaseURL': settings.FIREBASE_CONFIG.get('database_url', '')
                })
                _firebase_initialized = True
                logger.info("Firebase Admin SDK inicializado desde archivo JSON")
                return True
        
        # Si no hay archivo, usar variables de entorno (método anterior)
        config = settings.FIREBASE_CONFIG
        
        # Validar que existan las credenciales necesarias
        if not config.get('project_id'):
            logger.warning("FIREBASE_PROJECT_ID no está configurado - Firebase deshabilitado")
            return False
        
        # Crear credenciales desde el diccionario de configuración
        cred_dict = {
            "type": "service_account",
            "project_id": config['project_id'],
            "private_key_id": config.get('private_key_id', ''),
            "private_key": config.get('private_key', ''),
            "client_email": config.get('client_email', ''),
            "client_id": config.get('client_id', ''),
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        }
        
        cred = credentials.Certificate(cred_dict)
        
        firebase_admin.initialize_app(cred, {
            'databaseURL': config['database_url']
        })
        
        _firebase_initialized = True
        logger.info("Firebase Admin SDK inicializado correctamente")
        return True
        
    except Exception as e:
        logger.error(f"Error al inicializar Firebase: {str(e)}")
        return False


def get_live_status(device_id: str) -> Optional[Dict]:
    """
    Obtiene el estado en vivo de un dispositivo desde Firebase.
    
    Lee la ruta: /status/{device_id}/live
    
    Args:
        device_id: ID del dispositivo (ej: "DEVICE_001")
    
    Returns:
        Dict con campos:
            - temp (float): Temperatura actual en °C
            - state (str): Estado actual (NORMAL, DESHIELO, FALLA, etc.)
            - ts (int): Timestamp en milisegundos
        None si no hay datos
    
    Example:
        >>> status = get_live_status("DEVICE_001")
        >>> print(f"Temperatura: {status['temp']}°C")
    """
    if not _firebase_initialized:
        initialize_firebase()
    
    try:
        ref = db.reference(f'/status/{device_id}/live')
        data = ref.get()
        
        if data:
            logger.debug(f"Estado en vivo obtenido para {device_id}: {data}")
            return data
        else:
            logger.warning(f"No hay datos en vivo para el dispositivo {device_id}")
            return None
            
    except Exception as e:
        logger.error(f"Error al obtener estado en vivo de {device_id}: {str(e)}")
        return None


def get_daily_controls(device_id: str, target_date: date) -> List[Dict]:
    """
    Obtiene los controles diarios de un dispositivo (4 lecturas al día).
    
    Lee la ruta: /controles/{device_id}/{año}/{mes}/{día}
    
    Args:
        device_id: ID del dispositivo
        target_date: Fecha de los controles a obtener
    
    Returns:
        Lista de diccionarios, cada uno con:
            - hour (str): Hora del control (08, 13, 16, 20)
            - temp (float): Temperatura medida
            - state (str): Estado de la cámara
            - ts (int): Timestamp en milisegundos
    
    Example:
        >>> from datetime import date
        >>> controls = get_daily_controls("DEVICE_001", date(2025, 12, 8))
        >>> for control in controls:
        >>>     print(f"{control['hour']}:00 - {control['temp']}°C")
    """
    if not _firebase_initialized:
        initialize_firebase()
    
    try:
        year = target_date.year
        month = str(target_date.month).zfill(2)
        day = str(target_date.day).zfill(2)
        
        ref = db.reference(f'/controles/{device_id}/{year}/{month}/{day}')
        data = ref.get()
        
        if not data:
            logger.info(f"No hay controles para {device_id} en {target_date}")
            return []
        
        # Convertir el diccionario de horas en una lista
        controls = []
        for hour, control_data in data.items():
            controls.append({
                'hour': hour,
                **control_data
            })
        
        # Ordenar por hora
        controls.sort(key=lambda x: x['hour'])
        
        logger.debug(f"Obtenidos {len(controls)} controles para {device_id} en {target_date}")
        return controls
        
    except Exception as e:
        logger.error(f"Error al obtener controles de {device_id} para {target_date}: {str(e)}")
        return []


def get_firebase_events(device_id: str, target_date: date) -> List[Dict]:
    """
    Obtiene los eventos de temperatura de un dispositivo en una fecha específica.
    
    Lee la ruta: /eventos/{device_id}/{año}/{mes}/{día}
    
    Args:
        device_id: ID del dispositivo
        target_date: Fecha de los eventos a obtener
    
    Returns:
        Lista de diccionarios, cada uno con:
            - event_id (str): ID del evento
            - type (str): Tipo de evento (DESHIELO_N, DESHIELO_P, FALLA, etc.)
            - start_ts (int): Timestamp de inicio
            - end_ts (int): Timestamp de fin (puede ser None)
            - duration_ms (int): Duración en milisegundos
            - max_temp (float): Temperatura máxima durante el evento
            - ended (bool): Si el evento ya finalizó
    
    Example:
        >>> events = get_firebase_events("DEVICE_001", date(2025, 12, 8))
        >>> for event in events:
        >>>     print(f"Evento {event['type']}: {event['max_temp']}°C")
    """
    if not _firebase_initialized:
        initialize_firebase()
    
    try:
        year = target_date.year
        month = str(target_date.month).zfill(2)
        day = str(target_date.day).zfill(2)
        
        ref = db.reference(f'/eventos/{device_id}/{year}/{month}/{day}')
        data = ref.get()
        
        if not data:
            logger.info(f"No hay eventos para {device_id} en {target_date}")
            return []
        
        # Convertir el diccionario de eventos en una lista
        events = []
        for event_id, event_data in data.items():
            events.append({
                'event_id': event_id,
                **event_data
            })
        
        # Ordenar por timestamp de inicio
        events.sort(key=lambda x: x.get('start_ts', 0))
        
        logger.debug(f"Obtenidos {len(events)} eventos para {device_id} en {target_date}")
        return events
        
    except Exception as e:
        logger.error(f"Error al obtener eventos de {device_id} para {target_date}: {str(e)}")
        return []


def get_all_devices() -> List[str]:
    """
    Obtiene la lista de todos los dispositivos registrados en Firebase.
    
    Lee la ruta: /status y extrae todos los device_id
    
    Returns:
        Lista de IDs de dispositivos
    
    Example:
        >>> devices = get_all_devices()
        >>> print(f"Total de dispositivos: {len(devices)}")
    """
    if not _firebase_initialized:
        initialize_firebase()
    
    try:
        ref = db.reference('/status')
        data = ref.get()
        
        if not data:
            logger.warning("No hay dispositivos registrados en Firebase")
            return []
        
        devices = list(data.keys())
        logger.info(f"Encontrados {len(devices)} dispositivos en Firebase")
        return devices
        
    except Exception as e:
        logger.error(f"Error al obtener lista de dispositivos: {str(e)}")
        return []


def get_device_status_readings(device_id: str, target_date: date) -> List[Dict]:
    """
    Obtiene las lecturas de status de un dispositivo en una fecha específica.
    
    Lee la ruta: /status/{device_id}/{año}/{mes}/{día}
    
    Args:
        device_id: ID del dispositivo
        target_date: Fecha de las lecturas a obtener
    
    Returns:
        Lista de diccionarios, cada uno con:
            - ts (int): Timestamp en segundos
            - temp (float): Temperatura medida
            - state (str): Estado de la cámara
    
    Example:
        >>> readings = get_device_status_readings("camara1", date(2025, 12, 8))
        >>> for reading in readings:
        >>>     print(f"{reading['ts']}: {reading['temp']}°C")
    """
    if not _firebase_initialized:
        initialize_firebase()
    
    try:
        year = target_date.year
        month = str(target_date.month).zfill(2)
        day = str(target_date.day).zfill(2)
        
        ref = db.reference(f'/status/{device_id}/{year}/{month}/{day}')
        data = ref.get()
        
        if not data:
            logger.info(f"No hay lecturas de status para {device_id} en {target_date}")
            return []
        
        # Convertir el diccionario de timestamps en una lista
        readings = []
        for timestamp_key, reading_data in data.items():
            if timestamp_key != 'live':  # Excluir el nodo 'live'
                readings.append({
                    'ts': int(timestamp_key),
                    'temp': reading_data.get('temp', 0),
                    'state': reading_data.get('state', 'UNKNOWN')
                })
        
        # Ordenar por timestamp
        readings.sort(key=lambda x: x['ts'])
        
        logger.debug(f"Obtenidas {len(readings)} lecturas de status para {device_id} en {target_date}")
        return readings
        
    except Exception as e:
        logger.error(f"Error al obtener lecturas de status de {device_id} para {target_date}: {str(e)}")
        return []


def get_device_status_history(device_id: str, start_date: date, end_date: date) -> List[Dict]:
    """
    Obtiene el histórico de controles de un dispositivo en un rango de fechas.
    
    Args:
        device_id: ID del dispositivo
        start_date: Fecha de inicio
        end_date: Fecha de fin
    
    Returns:
        Lista de todos los controles en el rango de fechas
    
    Example:
        >>> from datetime import date, timedelta
        >>> today = date.today()
        >>> week_ago = today - timedelta(days=7)
        >>> history = get_device_status_history("DEVICE_001", week_ago, today)
    """
    if not _firebase_initialized:
        initialize_firebase()
    
    all_controls = []
    current_date = start_date
    
    while current_date <= end_date:
        controls = get_daily_controls(device_id, current_date)
        for control in controls:
            control['date'] = current_date.isoformat()
        all_controls.extend(controls)
        current_date = date.fromordinal(current_date.toordinal() + 1)
    
    logger.info(f"Obtenidos {len(all_controls)} controles históricos para {device_id}")
    return all_controls
