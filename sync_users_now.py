"""
Script para sincronizar usuarios de Firebase Auth a Supabase
"""
import os
import sys
import django

# Configurar Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'coldtrack.settings')
django.setup()

from firebase_admin import auth
import requests
from django.conf import settings

def sync_users():
    """Sincronizar todos los usuarios de Firebase Auth a Supabase"""
    
    config = settings.SUPABASE_CONFIG
    headers = {
        'apikey': config['service_key'],
        'Authorization': f'Bearer {config["service_key"]}',
        'Content-Type': 'application/json',
        'Prefer': 'return=representation'
    }
    
    print("🔄 Obteniendo usuarios de Firebase Auth...")
    
    # Obtener todos los usuarios de Firebase
    page = auth.list_users()
    users_synced = 0
    
    while page:
        for user in page.users:
            print(f"\n📝 Procesando usuario: {user.email}")
            
            # Verificar si el usuario ya existe en Supabase
            check_url = f'{config["url"]}/rest/v1/usuarios?firebase_uid=eq.{user.uid}'
            check_response = requests.get(check_url, headers=headers)
            
            if check_response.status_code == 200 and len(check_response.json()) > 0:
                print(f"   ✅ Usuario ya existe en Supabase")
                continue
            
            # Crear usuario en Supabase
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
                print(f"   ✅ Usuario creado en Supabase")
                users_synced += 1
            else:
                print(f"   ❌ Error al crear usuario: {create_response.text}")
        
        # Siguiente página
        page = page.get_next_page()
    
    print(f"\n🎉 Sincronización completada: {users_synced} usuarios sincronizados")

if __name__ == '__main__':
    sync_users()
