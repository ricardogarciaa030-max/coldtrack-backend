#!/usr/bin/env python3
"""
Generador de datos de prueba para DICIEMBRE 2025 (1-13 diciembre)
Genera lecturas de temperatura y eventos realistas para el sistema ColdTrack
"""

import os
import sys
import django
from datetime import datetime, timedelta
import random
import uuid

# Configurar Django
sys.path.append('/workspaces/coldtrack')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'coldtrack.settings')
django.setup()

from services.supabase_service import get_supabase_client

def generate_december_data():
    """Genera datos completos para diciembre 1-13, 2025"""
    
    print("🎄 GENERANDO DATOS DE DICIEMBRE 2025 (1-13)")
    print("=" * 60)
    
    client = get_supabase_client(use_service_key=True)
    
    # Configuración
    CAMARA_ID = 3  # Cámara principal
    FECHA_INICIO = datetime(2025, 12, 1)
    FECHA_FIN = datetime(2025, 12, 13, 23, 59, 59)
    
    # Rangos de temperatura realistas para refrigeración
    TEMP_NORMAL_MIN = -8.0    # Temperatura mínima normal
    TEMP_NORMAL_MAX = -2.0    # Temperatura máxima normal
    TEMP_DESHIELO_MIN = 1.0   # Durante deshielo
    TEMP_DESHIELO_MAX = 4.0   # Durante deshielo
    TEMP_FALLA_MIN = 6.0      # Durante falla
    TEMP_FALLA_MAX = 12.0     # Durante falla crítica
    
    lecturas_generadas = []
    eventos_generados = []
    
    # Generar datos día por día
    fecha_actual = FECHA_INICIO
    
    while fecha_actual <= FECHA_FIN:
        print(f"📅 Generando datos para {fecha_actual.strftime('%Y-%m-%d')}")
        
        # Generar lecturas cada minuto durante el día
        for minuto in range(0, 1440):  # 1440 minutos en un día
            timestamp = fecha_actual + timedelta(minutes=minuto)
            
            # Temperatura base normal con variación natural
            temp_base = random.uniform(TEMP_NORMAL_MIN, TEMP_NORMAL_MAX)
            
            # Agregar variación natural pequeña
            variacion = random.uniform(-0.5, 0.5)
            temperatura = round(temp_base + variacion, 1)
            
            lectura = {
                'camara_id': CAMARA_ID,
                'temperatura_c': temperatura,
                'timestamp': timestamp.isoformat()
            }
            
            lecturas_generadas.append(lectura)
        
        # Generar eventos del día (2-3 deshielos + posibles fallas)
        eventos_del_dia = []
        
        # Deshielo matutino (6:00-7:00 AM)
        hora_deshielo_1 = fecha_actual.replace(hour=6, minute=random.randint(0, 30))
        duracion_1 = random.randint(25, 45)  # 25-45 minutos
        temp_max_1 = round(random.uniform(TEMP_DESHIELO_MIN, TEMP_DESHIELO_MAX), 1)
        
        evento_1 = {
            'firebase_event_id': f"dec_event_{hora_deshielo_1.strftime('%Y%m%d_%H%M%S')}_deshielo1",
            'camara_id': CAMARA_ID,
            'tipo': 'DESHIELO_N',  # Deshielo normal
            'estado': 'COMPLETADO',
            'fecha_inicio': hora_deshielo_1.isoformat(),
            'fecha_fin': (hora_deshielo_1 + timedelta(minutes=duracion_1)).isoformat(),
            'temp_max_c': temp_max_1,
            'duracion_minutos': duracion_1,
            'created_at': datetime.now().isoformat()
        }
        eventos_del_dia.append(evento_1)
        
        # Deshielo vespertino (6:00-8:00 PM)
        hora_deshielo_2 = fecha_actual.replace(hour=18, minute=random.randint(0, 60))
        duracion_2 = random.randint(30, 50)  # 30-50 minutos
        temp_max_2 = round(random.uniform(TEMP_DESHIELO_MIN, TEMP_DESHIELO_MAX), 1)
        
        evento_2 = {
            'firebase_event_id': f"dec_event_{hora_deshielo_2.strftime('%Y%m%d_%H%M%S')}_deshielo2",
            'camara_id': CAMARA_ID,
            'tipo': 'DESHIELO_P',  # Deshielo programado
            'estado': 'COMPLETADO',
            'fecha_inicio': hora_deshielo_2.isoformat(),
            'fecha_fin': (hora_deshielo_2 + timedelta(minutes=duracion_2)).isoformat(),
            'temp_max_c': temp_max_2,
            'duracion_minutos': duracion_2,
            'created_at': datetime.now().isoformat()
        }
        eventos_del_dia.append(evento_2)
        
        # Posible tercer deshielo (medianoche) - 40% probabilidad
        if random.random() < 0.4:
            hora_deshielo_3 = fecha_actual.replace(hour=0, minute=random.randint(0, 30))
            duracion_3 = random.randint(20, 35)
            temp_max_3 = round(random.uniform(TEMP_DESHIELO_MIN, TEMP_DESHIELO_MAX), 1)
            
            evento_3 = {
                'firebase_event_id': f"dec_event_{hora_deshielo_3.strftime('%Y%m%d_%H%M%S')}_deshielo3",
                'camara_id': CAMARA_ID,
                'tipo': 'DESHIELO_N',
                'estado': 'COMPLETADO',
                'fecha_inicio': hora_deshielo_3.isoformat(),
                'fecha_fin': (hora_deshielo_3 + timedelta(minutes=duracion_3)).isoformat(),
                'temp_max_c': temp_max_3,
                'duracion_minutos': duracion_3,
                'created_at': datetime.now().isoformat()
            }
            eventos_del_dia.append(evento_3)
        
        # Posible falla (10% probabilidad por día)
        if random.random() < 0.1:
            hora_falla = fecha_actual.replace(
                hour=random.randint(8, 16), 
                minute=random.randint(0, 59)
            )
            duracion_falla = random.randint(45, 120)  # 45-120 minutos de falla
            temp_max_falla = round(random.uniform(TEMP_FALLA_MIN, TEMP_FALLA_MAX), 1)
            
            evento_falla = {
                'firebase_event_id': f"dec_event_{hora_falla.strftime('%Y%m%d_%H%M%S')}_falla",
                'camara_id': CAMARA_ID,
                'tipo': 'FALLA',
                'estado': 'COMPLETADO',
                'fecha_inicio': hora_falla.isoformat(),
                'fecha_fin': (hora_falla + timedelta(minutes=duracion_falla)).isoformat(),
                'temp_max_c': temp_max_falla,
                'duracion_minutos': duracion_falla,
                'created_at': datetime.now().isoformat()
            }
            eventos_del_dia.append(evento_falla)
        
        eventos_generados.extend(eventos_del_dia)
        
        # Actualizar temperaturas durante eventos
        for evento in eventos_del_dia:
            inicio = datetime.fromisoformat(evento['fecha_inicio'])
            fin = datetime.fromisoformat(evento['fecha_fin'])
            temp_evento = evento['temp_max_c']
            
            # Actualizar lecturas durante el evento
            for lectura in lecturas_generadas:
                lectura_time = datetime.fromisoformat(lectura['timestamp'])
                if inicio <= lectura_time <= fin:
                    # Temperatura gradual durante el evento
                    minutos_transcurridos = (lectura_time - inicio).total_seconds() / 60
                    progreso = minutos_transcurridos / evento['duracion_minutos']
                    
                    if progreso <= 0.5:
                        # Subida gradual
                        temp_actual = TEMP_NORMAL_MAX + (temp_evento - TEMP_NORMAL_MAX) * (progreso * 2)
                    else:
                        # Bajada gradual
                        temp_actual = temp_evento - (temp_evento - TEMP_NORMAL_MAX) * ((progreso - 0.5) * 2)
                    
                    lectura['temperatura_c'] = round(temp_actual + random.uniform(-0.3, 0.3), 1)
        
        # Avanzar al siguiente día
        fecha_actual += timedelta(days=1)
    
    print(f"\n📊 RESUMEN DE DATOS GENERADOS:")
    print(f"   📈 Lecturas de temperatura: {len(lecturas_generadas)}")
    print(f"   ⚡ Eventos generados: {len(eventos_generados)}")
    
    # Contar tipos de eventos
    deshielos = len([e for e in eventos_generados if e['tipo'] in ['DESHIELO_N', 'DESHIELO_P']])
    fallas = len([e for e in eventos_generados if e['tipo'] == 'FALLA'])
    
    print(f"   ❄️ Deshielos: {deshielos}")
    print(f"   🚨 Fallas: {fallas}")
    
    # Insertar lecturas en lotes
    print(f"\n💾 INSERTANDO LECTURAS EN SUPABASE...")
    batch_size = 1000
    lecturas_insertadas = 0
    
    for i in range(0, len(lecturas_generadas), batch_size):
        batch = lecturas_generadas[i:i + batch_size]
        try:
            result = client.table('lecturas_temperatura').insert(batch).execute()
            lecturas_insertadas += len(batch)
            print(f"   ✅ Insertadas {lecturas_insertadas}/{len(lecturas_generadas)} lecturas")
        except Exception as e:
            print(f"   ❌ Error insertando lote {i//batch_size + 1}: {e}")
    
    # Insertar eventos
    print(f"\n⚡ INSERTANDO EVENTOS EN SUPABASE...")
    try:
        result = client.table('eventos_temperatura').insert(eventos_generados).execute()
        print(f"   ✅ {len(eventos_generados)} eventos insertados exitosamente")
    except Exception as e:
        print(f"   ❌ Error insertando eventos: {e}")
    
    print(f"\n🎉 GENERACIÓN COMPLETADA PARA DICIEMBRE 1-13, 2025")
    print(f"   📅 Período: 2025-12-01 a 2025-12-13")
    print(f"   📊 Total lecturas: {len(lecturas_generadas)}")
    print(f"   ⚡ Total eventos: {len(eventos_generados)}")
    print(f"   🏭 Cámara: {CAMARA_ID}")

if __name__ == "__main__":
    generate_december_data()