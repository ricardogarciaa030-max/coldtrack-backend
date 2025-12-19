"""
Script para verificar que la sincronización funcionó correctamente
"""
import os
import django
import sys

# Configurar Django
sys.path.append(os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'coldtrack.settings')
django.setup()

from services.supabase_service import get_supabase_client

def verify_sync():
    client = get_supabase_client(use_service_key=True)
    
    print("🔍 Verificando sincronización...")
    
    # Últimos eventos con firebase_event_id
    result = client.table('eventos_temperatura')\
        .select('id, firebase_event_id, tipo, estado, fecha_inicio')\
        .order('id', desc=True)\
        .limit(10)\
        .execute()
    
    print("\n📋 Últimos 10 eventos:")
    for evento in result.data:
        firebase_id = evento['firebase_event_id'] or 'NULL'
        print(f"  ID: {evento['id']} | Firebase: {firebase_id} | Tipo: {evento['tipo']} | Estado: {evento['estado']}")
    
    # Contar eventos con firebase_event_id
    count_with_id = client.table('eventos_temperatura')\
        .select('id', count='exact')\
        .not_.is_('firebase_event_id', 'null')\
        .execute()
    
    count_total = client.table('eventos_temperatura')\
        .select('id', count='exact')\
        .execute()
    
    print(f"\n📊 Estadísticas:")
    print(f"  Total eventos: {count_total.count}")
    print(f"  Con firebase_event_id: {count_with_id.count}")
    print(f"  Sin firebase_event_id: {count_total.count - count_with_id.count}")
    
    # Verificar eventos EN_CURSO
    en_curso = client.table('eventos_temperatura')\
        .select('id, firebase_event_id, tipo')\
        .eq('estado', 'EN_CURSO')\
        .execute()
    
    print(f"\n🔴 Eventos EN_CURSO: {len(en_curso.data)}")
    for evento in en_curso.data:
        firebase_id = evento['firebase_event_id'] or 'NULL'
        print(f"  ID: {evento['id']} | Firebase: {firebase_id} | Tipo: {evento['tipo']}")

if __name__ == "__main__":
    verify_sync()