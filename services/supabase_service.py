"""
Supabase Service

Este módulo centraliza todas las interacciones con Supabase PostgreSQL.
Proporciona funciones para insertar y consultar datos históricos.

Funciones principales:
- get_supabase_client(): Obtiene cliente de Supabase
- insert_temperature_reading(): Inserta una lectura de temperatura
- insert_event(): Inserta un evento de temperatura
- update_event_end(): Actualiza el fin de un evento
- insert_daily_summary(): Inserta o actualiza resumen diario
- get_camera_by_firebase_path(): Busca cámara por su firebase_path
"""

from supabase import create_client, Client
from django.conf import settings
import logging
from datetime import datetime, date
from typing import Dict, List, Optional
from decimal import Decimal

logger = logging.getLogger(__name__)

# Variable global para mantener el cliente de Supabase
_supabase_client: Optional[Client] = None


def get_supabase_client(use_service_key: bool = False) -> Client:
    """
    Obtiene o crea el cliente de Supabase.
    
    Esta función mantiene una única instancia del cliente para reutilizar
    la conexión en múltiples llamadas.
    
    Args:
        use_service_key: Si True, usa la service_key en lugar de anon_key
                        (necesario para bypass RLS en operaciones de autenticación)
    
    Returns:
        Client: Cliente de Supabase inicializado
    
    Raises:
        ValueError: Si faltan credenciales de Supabase
    """
    global _supabase_client
    
    # Si se solicita service_key, crear un nuevo cliente cada vez
    # (no cachear porque puede alternarse entre anon y service)
    if use_service_key:
        try:
            config = settings.SUPABASE_CONFIG
            
            if not config.get('url') or not config.get('service_key'):
                raise ValueError("Service key de Supabase no configurada")
            
            service_client = create_client(
                supabase_url=config['url'],
                supabase_key=config['service_key']
            )
            
            logger.debug("Cliente de Supabase con service_key creado")
            return service_client
            
        except Exception as e:
            logger.error(f"Error al crear cliente con service_key: {str(e)}")
            raise
    
    # Cliente normal con anon_key (cacheado)
    if _supabase_client is not None:
        return _supabase_client
    
    try:
        config = settings.SUPABASE_CONFIG
        
        if not config.get('url') or not config.get('anon_key'):
            raise ValueError("Credenciales de Supabase no configuradas")
        
        # Crear cliente sin opciones adicionales para compatibilidad
        _supabase_client = create_client(
            supabase_url=config['url'],
            supabase_key=config['anon_key']
        )
        
        logger.info("Cliente de Supabase inicializado correctamente")
        return _supabase_client
        
    except Exception as e:
        logger.error(f"Error al inicializar cliente de Supabase: {str(e)}")
        raise


def get_camera_by_firebase_path(firebase_path: str) -> Optional[Dict]:
    """
    Busca una cámara por su firebase_path (device_id).
    
    Args:
        firebase_path: Path de Firebase del dispositivo (ej: "DEVICE_001")
    
    Returns:
        Dict con los datos de la cámara o None si no existe
        Campos: id, nombre, codigo, sucursal_id, tipo, activa
    
    Example:
        >>> camera = get_camera_by_firebase_path("DEVICE_001")
        >>> if camera:
        >>>     print(f"Cámara: {camera['nombre']}")
    """
    try:
        client = get_supabase_client(use_service_key=True)
        
        response = client.table('camaras_frio')\
            .select('*')\
            .eq('firebase_path', firebase_path)\
            .eq('activa', True)\
            .execute()
        
        if response.data and len(response.data) > 0:
            logger.debug(f"Cámara encontrada para firebase_path {firebase_path}")
            return response.data[0]
        else:
            logger.warning(f"No se encontró cámara con firebase_path {firebase_path}")
            return None
            
    except Exception as e:
        logger.error(f"Error al buscar cámara por firebase_path {firebase_path}: {str(e)}")
        return None


def insert_temperature_reading(
    camara_id: int,
    timestamp: datetime,
    temperatura_c: float,
    origen: str
) -> Optional[Dict]:
    """
    Inserta una lectura de temperatura en la base de datos.
    
    Args:
        camara_id: ID de la cámara en Supabase
        timestamp: Fecha y hora de la lectura
        temperatura_c: Temperatura en grados Celsius
        origen: Origen de la lectura (ej: "firebase:status", "firebase:controles")
    
    Returns:
        Dict con los datos insertados o None si hubo error
    
    Example:
        >>> from datetime import datetime
        >>> reading = insert_temperature_reading(
        >>>     camara_id=1,
        >>>     timestamp=datetime.now(),
        >>>     temperatura_c=2.5,
        >>>     origen="firebase:status"
        >>> )
    """
    try:
        client = get_supabase_client(use_service_key=True)
        
        data = {
            'camara_id': camara_id,
            'timestamp': timestamp.isoformat(),
            'temperatura_c': float(temperatura_c),
            'origen': origen
        }
        
        response = client.table('lecturas_temperatura')\
            .insert(data)\
            .execute()
        
        if response.data:
            logger.debug(f"Lectura insertada para cámara {camara_id}: {temperatura_c}°C")
            return response.data[0]
        else:
            logger.error(f"No se pudo insertar lectura para cámara {camara_id}")
            return None
            
    except Exception as e:
        logger.error(f"Error al insertar lectura de temperatura: {str(e)}")
        return None


def insert_event(
    camara_id: int,
    fecha_inicio: datetime,
    tipo: str,
    temp_max_c: float,
    fecha_fin: Optional[datetime] = None,
    duracion_minutos: Optional[int] = None,
    estado: str = 'DETECTADO',
    observaciones: Optional[str] = None
) -> Optional[Dict]:
    """
    Inserta un evento de temperatura en la base de datos.
    
    Args:
        camara_id: ID de la cámara
        fecha_inicio: Fecha y hora de inicio del evento
        tipo: Tipo de evento (DESHIELO_N, DESHIELO_P, FALLA, etc.)
        temp_max_c: Temperatura máxima durante el evento
        fecha_fin: Fecha y hora de fin (opcional, None si está en curso)
        duracion_minutos: Duración en minutos (opcional)
        estado: Estado del evento (DETECTADO, EN_CURSO, RESUELTO)
        observaciones: Observaciones adicionales (opcional)
    
    Returns:
        Dict con los datos del evento insertado o None si hubo error
    
    Example:
        >>> event = insert_event(
        >>>     camara_id=1,
        >>>     fecha_inicio=datetime.now(),
        >>>     tipo="DESHIELO_N",
        >>>     temp_max_c=8.5,
        >>>     estado="EN_CURSO"
        >>> )
    """
    try:
        client = get_supabase_client(use_service_key=True)
        
        data = {
            'camara_id': camara_id,
            'fecha_inicio': fecha_inicio.isoformat(),
            'tipo': tipo,
            'temp_max_c': float(temp_max_c),
            'estado': estado
        }
        
        if fecha_fin:
            data['fecha_fin'] = fecha_fin.isoformat()
        
        if duracion_minutos is not None:
            data['duracion_minutos'] = duracion_minutos
        
        if observaciones:
            data['observaciones'] = observaciones
        
        response = client.table('eventos_temperatura')\
            .insert(data)\
            .execute()
        
        if response.data:
            logger.info(f"Evento insertado para cámara {camara_id}: {tipo}")
            return response.data[0]
        else:
            logger.error(f"No se pudo insertar evento para cámara {camara_id}")
            return None
            
    except Exception as e:
        logger.error(f"Error al insertar evento: {str(e)}")
        return None


def update_event_end(
    event_id: int,
    fecha_fin: datetime,
    duracion_minutos: int,
    estado: str = 'RESUELTO'
) -> Optional[Dict]:
    """
    Actualiza el fin de un evento que estaba en curso.
    
    Args:
        event_id: ID del evento en Supabase
        fecha_fin: Fecha y hora de fin del evento
        duracion_minutos: Duración total en minutos
        estado: Nuevo estado del evento (por defecto RESUELTO)
    
    Returns:
        Dict con los datos actualizados o None si hubo error
    
    Example:
        >>> updated = update_event_end(
        >>>     event_id=123,
        >>>     fecha_fin=datetime.now(),
        >>>     duracion_minutos=60,
        >>>     estado="RESUELTO"
        >>> )
    """
    try:
        client = get_supabase_client()
        
        data = {
            'fecha_fin': fecha_fin.isoformat(),
            'duracion_minutos': duracion_minutos,
            'estado': estado
        }
        
        response = client.table('eventos_temperatura')\
            .update(data)\
            .eq('id', event_id)\
            .execute()
        
        if response.data:
            logger.info(f"Evento {event_id} actualizado con fecha de fin")
            return response.data[0]
        else:
            logger.error(f"No se pudo actualizar evento {event_id}")
            return None
            
    except Exception as e:
        logger.error(f"Error al actualizar evento {event_id}: {str(e)}")
        return None


def insert_daily_summary(
    fecha: date,
    camara_id: int,
    temp_min: float,
    temp_max: float,
    temp_promedio: float,
    total_lecturas: int,
    alertas_descongelamiento: int = 0,
    fallas_detectadas: int = 0
) -> Optional[Dict]:
    """
    Inserta o actualiza un resumen diario de una cámara.
    
    Si ya existe un resumen para esa fecha y cámara, lo actualiza.
    
    Args:
        fecha: Fecha del resumen
        camara_id: ID de la cámara
        temp_min: Temperatura mínima del día
        temp_max: Temperatura máxima del día
        temp_promedio: Temperatura promedio del día
        total_lecturas: Total de lecturas registradas
        alertas_descongelamiento: Cantidad de alertas de descongelamiento
        fallas_detectadas: Cantidad de fallas detectadas
    
    Returns:
        Dict con los datos del resumen o None si hubo error
    
    Example:
        >>> summary = insert_daily_summary(
        >>>     fecha=date.today(),
        >>>     camara_id=1,
        >>>     temp_min=1.5,
        >>>     temp_max=3.2,
        >>>     temp_promedio=2.3,
        >>>     total_lecturas=96
        >>> )
    """
    try:
        client = get_supabase_client(use_service_key=True)
        
        # Verificar si ya existe un resumen para esta fecha y cámara
        existing = client.table('resumen_diario_camara')\
            .select('id')\
            .eq('fecha', fecha.isoformat())\
            .eq('camara_id', camara_id)\
            .execute()
        
        data = {
            'fecha': fecha.isoformat(),
            'camara_id': camara_id,
            'temp_min': float(temp_min),
            'temp_max': float(temp_max),
            'temp_promedio': float(temp_promedio),
            'total_lecturas': total_lecturas,
            'alertas_descongelamiento': alertas_descongelamiento,
            'fallas_detectadas': fallas_detectadas
        }
        
        if existing.data and len(existing.data) > 0:
            # Actualizar resumen existente
            response = client.table('resumen_diario_camara')\
                .update(data)\
                .eq('id', existing.data[0]['id'])\
                .execute()
            logger.info(f"Resumen diario actualizado para cámara {camara_id} en {fecha}")
        else:
            # Insertar nuevo resumen
            response = client.table('resumen_diario_camara')\
                .insert(data)\
                .execute()
            logger.info(f"Resumen diario insertado para cámara {camara_id} en {fecha}")
        
        if response.data:
            return response.data[0]
        else:
            logger.error(f"No se pudo guardar resumen diario para cámara {camara_id}")
            return None
            
    except Exception as e:
        logger.error(f"Error al insertar/actualizar resumen diario: {str(e)}")
        return None


def get_open_events_for_camera(camara_id: int) -> List[Dict]:
    """
    Obtiene todos los eventos abiertos (sin fecha_fin) de una cámara.
    
    Args:
        camara_id: ID de la cámara
    
    Returns:
        Lista de eventos abiertos
    
    Example:
        >>> open_events = get_open_events_for_camera(1)
        >>> print(f"Eventos abiertos: {len(open_events)}")
    """
    try:
        client = get_supabase_client()
        
        response = client.table('eventos_temperatura')\
            .select('*')\
            .eq('camara_id', camara_id)\
            .is_('fecha_fin', 'null')\
            .execute()
        
        if response.data:
            logger.debug(f"Encontrados {len(response.data)} eventos abiertos para cámara {camara_id}")
            return response.data
        else:
            return []
            
    except Exception as e:
        logger.error(f"Error al obtener eventos abiertos: {str(e)}")
        return []
