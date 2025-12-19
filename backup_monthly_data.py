"""
Sistema de respaldo mensual automático
Guarda todos los datos de Firebase en Supabase antes de que se borren
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
from datetime import datetime, date, timedelta
import logging
import calendar

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def backup_month_data(year, month):
    """
    Hacer respaldo completo de un mes específico
    """
    try:
        initialize_firebase()
        client = get_supabase_client(use_service_key=True)
        
        logger.info(f"🗄️  Iniciando respaldo del mes {month}/{year}...")
        
        # Obtener todos los dispositivos
        events_ref = db.reference('eventos')
        events_data = events_ref.get()
        
        if not events_data:
            logger.warning("No hay datos de eventos en Firebase")
            return
        
        total_eventos = 0
        total_lecturas = 0
        
        for device_id, device_events in events_data.items():
            # Buscar cámara en Supabase
            camera = get_camera_by_firebase_path(device_id)
            if not camera:
                logger.warning(f"Cámara no encontrada: {device_id}")
                continue
            
            logger.info(f"📱 Procesando device: {device_id}")
            
            # Navegar a año/mes específico
            year_data = device_events.get(str(year), {})
            month_data = year_data.get(f"{month:02d}", {})
            
            if not month_data:
                logger.info(f"  No hay datos para {month:02d}/{year}")
                continue
            
            # Procesar cada día del mes
            for day, day_data in month_data.items():
                if not isinstance(day_data, dict):
                    continue
                
                logger.info(f"  📅 Procesando día {day}")
                
                # Procesar cada evento del día
                for event_id, event_data in day_data.items():
                    if not isinstance(event_data, dict):
                        continue
                    
                    try:
                        # Verificar si ya existe en Supabase
                        existing_response = client.table('eventos_temperatura')\
                            .select('id')\
                            .eq('firebase_event_id', event_id)\
                            .execute()
                        
                        if not existing_response.data:
                            # Crear evento en Supabase
                            resultado = create_event_from_firebase(client, camera, event_id, event_data)
                            if resultado:
                                total_eventos += 1
                                logger.info(f"    ✅ Respaldado evento: {event_id}")
                        else:
                            logger.debug(f"    ℹ️  Evento ya existe: {event_id}")
                            
                    except Exception as e:
                        logger.error(f"    ❌ Error respaldando evento {event_id}: {str(e)}")
        
        # Respaldar temperaturas del mes
        total_lecturas = backup_temperature_data(year, month)
        
        logger.info(f"🎉 Respaldo completado para {month}/{year}:")
        logger.info(f"  📊 Eventos respaldados: {total_eventos}")
        logger.info(f"  🌡️  Lecturas respaldadas: {total_lecturas}")
        
        # Crear registro de respaldo
        create_backup_record(client, year, month, total_eventos, total_lecturas)
        
    except Exception as e:
        logger.error(f"Error en respaldo mensual: {str(e)}")
        import traceback
        traceback.print_exc()


def create_event_from_firebase(client, camera, firebase_event_id, event_data):
    """Crear evento en Supabase desde datos de Firebase"""
    try:
        # Extraer datos
        start_ts = event_data.get('start_ts')
        end_ts = event_data.get('end_ts')
        duration_ms = event_data.get('duration_ms', 0)
        max_temp = event_data.get('max_temp', 0)
        event_type = event_data.get('type', 'UNKNOWN')
        
        if not start_ts:
            return False
        
        # Convertir timestamps
        fecha_inicio = datetime.fromtimestamp(start_ts)
        fecha_fin = None
        if end_ts:
            fecha_fin = datetime.fromtimestamp(end_ts)
        
        # Calcular duración
        duracion_minutos = duration_ms // 60000 if duration_ms else 0
        estado = 'RESUELTO' if end_ts else 'EN_CURSO'
        
        # Insertar en Supabase
        insert_data = {
            'camara_id': camera['id'],
            'firebase_event_id': firebase_event_id,
            'fecha_inicio': fecha_inicio.isoformat(),
            'fecha_fin': fecha_fin.isoformat() if fecha_fin else None,
            'tipo': event_type,
            'temp_max_c': float(max_temp),
            'duracion_minutos': duracion_minutos,
            'estado': estado,
            'observaciones': f'Respaldo automático - Firebase ID: {firebase_event_id}'
        }
        
        result = client.table('eventos_temperatura')\
            .insert(insert_data)\
            .execute()
        
        return bool(result.data)
        
    except Exception as e:
        logger.error(f"Error creando evento desde Firebase: {str(e)}")
        return False


def backup_temperature_data(year, month):
    """Respaldar datos de temperatura del mes"""
    try:
        initialize_firebase()
        client = get_supabase_client(use_service_key=True)
        
        # Obtener datos de status
        status_ref = db.reference('status')
        status_data = status_ref.get()
        
        if not status_data:
            return 0
        
        total_lecturas = 0
        
        # Calcular rango de timestamps del mes
        first_day = datetime(year, month, 1)
        if month == 12:
            last_day = datetime(year + 1, 1, 1) - timedelta(seconds=1)
        else:
            last_day = datetime(year, month + 1, 1) - timedelta(seconds=1)
        
        start_timestamp = int(first_day.timestamp())
        end_timestamp = int(last_day.timestamp())
        
        logger.info(f"🌡️  Respaldando temperaturas {first_day.date()} a {last_day.date()}")
        
        for device_id, device_data in status_data.items():
            # Buscar cámara
            camera = get_camera_by_firebase_path(device_id)
            if not camera:
                continue
            
            if not isinstance(device_data, dict):
                continue
            
            # Procesar timestamps del mes
            for timestamp_key, reading_data in device_data.items():
                if not timestamp_key.isdigit():
                    continue
                
                timestamp_int = int(timestamp_key)
                
                # Verificar si está en el rango del mes
                if start_timestamp <= timestamp_int <= end_timestamp:
                    try:
                        fecha_lectura = datetime.fromtimestamp(timestamp_int)
                        
                        if isinstance(reading_data, dict):
                            temperatura = float(reading_data.get('temp', 0))
                        else:
                            temperatura = float(reading_data)
                        
                        # Verificar si ya existe
                        existing_response = client.table('lecturas_temperatura')\
                            .select('id')\
                            .eq('camara_id', camera['id'])\
                            .eq('timestamp', fecha_lectura.isoformat())\
                            .execute()
                        
                        if not existing_response.data:
                            # Crear lectura
                            insert_data = {
                                'camara_id': camera['id'],
                                'timestamp': fecha_lectura.isoformat(),
                                'temperatura_c': temperatura,
                                'origen': 'backup_monthly'
                            }
                            
                            result = client.table('lecturas_temperatura')\
                                .insert(insert_data)\
                                .execute()
                            
                            if result.data:
                                total_lecturas += 1
                    
                    except Exception as e:
                        logger.error(f"Error respaldando lectura {timestamp_key}: {str(e)}")
        
        return total_lecturas
        
    except Exception as e:
        logger.error(f"Error respaldando temperaturas: {str(e)}")
        return 0


def create_backup_record(client, year, month, eventos, lecturas):
    """Crear registro del respaldo realizado"""
    try:
        # Crear tabla de respaldos si no existe
        backup_data = {
            'year': year,
            'month': month,
            'fecha_respaldo': datetime.now().isoformat(),
            'eventos_respaldados': eventos,
            'lecturas_respaldadas': lecturas,
            'estado': 'COMPLETADO'
        }
        
        # Intentar insertar (la tabla puede no existir)
        try:
            result = client.table('respaldos_mensuales')\
                .insert(backup_data)\
                .execute()
            logger.info(f"📝 Registro de respaldo creado: {year}-{month:02d}")
        except:
            logger.warning("⚠️  No se pudo crear registro de respaldo (tabla no existe)")
        
    except Exception as e:
        logger.error(f"Error creando registro de respaldo: {str(e)}")


def backup_current_month():
    """Respaldar el mes actual"""
    now = datetime.now()
    backup_month_data(now.year, now.month)


def backup_previous_month():
    """Respaldar el mes anterior (útil para fin de mes)"""
    now = datetime.now()
    if now.month == 1:
        # Si estamos en enero, respaldar diciembre del año anterior
        backup_month_data(now.year - 1, 12)
    else:
        backup_month_data(now.year, now.month - 1)


def schedule_end_of_month_backup():
    """
    Programar respaldo automático para fin de mes
    Ejecutar este script el día 28-31 de cada mes
    """
    now = datetime.now()
    
    # Verificar si estamos en los últimos días del mes
    last_day_of_month = calendar.monthrange(now.year, now.month)[1]
    
    if now.day >= 28:  # Últimos días del mes
        logger.info(f"🗓️  Fin de mes detectado (día {now.day}/{last_day_of_month})")
        logger.info("🚨 Ejecutando respaldo de emergencia del mes actual...")
        backup_current_month()
        
        # Si es el último día, también respaldar por seguridad
        if now.day == last_day_of_month:
            logger.info("🚨 ÚLTIMO DÍA DEL MES - Respaldo crítico")
    else:
        logger.info(f"📅 Día {now.day} del mes - No es necesario respaldo de emergencia")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "current":
            backup_current_month()
        elif sys.argv[1] == "previous":
            backup_previous_month()
        elif sys.argv[1] == "schedule":
            schedule_end_of_month_backup()
        elif sys.argv[1] == "month" and len(sys.argv) == 4:
            year = int(sys.argv[2])
            month = int(sys.argv[3])
            backup_month_data(year, month)
        else:
            print("Uso:")
            print("  python backup_monthly_data.py current     # Respaldar mes actual")
            print("  python backup_monthly_data.py previous    # Respaldar mes anterior")
            print("  python backup_monthly_data.py schedule    # Verificar si es fin de mes")
            print("  python backup_monthly_data.py month 2025 12  # Respaldar mes específico")
    else:
        # Por defecto, verificar si es fin de mes
        schedule_end_of_month_backup()