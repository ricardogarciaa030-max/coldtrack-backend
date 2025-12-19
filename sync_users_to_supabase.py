"""
Script para sincronizar usuarios de Firebase Auth a Supabase
"""
import os
import json
import requests

# Cargar variables de entorno manualmente
def load_env():
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value

load_env()

try:
    import firebase_admin
    from firebase_admin import credentials, auth
    
    # Cargar credenciales de Firebase
    creds_path = os.path.join(os.path.dirname(__file__), 'firebase-credentials.json')
    
    if not os.path.exists(creds_path):
        print(f"\nError: No se encontró el archivo {creds_path}")
        exit(1)
    
    print(f"\nCargando credenciales de Firebase...")
    
    cred = credentials.Certificate(creds_path)
    firebase_admin.initialize_app(cred)
    
    # Configurar Supabase - Usar SERVICE_KEY para bypass RLS
    SUPABASE_URL = os.getenv('SUPABASE_URL')
    SUPABASE_SERVICE_KEY = os.getenv('SUPABASE_SERVICE_KEY')
    
    if not SUPABASE_SERVICE_KEY:
        print("\n❌ Error: SUPABASE_SERVICE_KEY no está configurada en .env")
        print("Esta clave es necesaria para crear usuarios (bypass RLS)")
        exit(1)
    
    headers = {
        'apikey': SUPABASE_SERVICE_KEY,
        'Authorization': f'Bearer {SUPABASE_SERVICE_KEY}',
        'Content-Type': 'application/json',
        'Prefer': 'return=representation'
    }
    
    print("\n" + "="*80)
    print("SINCRONIZANDO USUARIOS DE FIREBASE A SUPABASE")
    print("="*80)
    
    # Listar usuarios de Firebase
    page = auth.list_users()
    users_synced = 0
    
    while page:
        for user in page.users:
            print(f"\nProcesando usuario: {user.email}")
            print(f"  UID: {user.uid}")
            
            # Determinar rol basado en el email
            if 'admin' in user.email.lower():
                rol = 'ADMIN'
            elif 'encargado' in user.email.lower():
                rol = 'ENCARGADO'
            elif 'subjefe' in user.email.lower():
                rol = 'SUBJEFE'
            else:
                # Por defecto, el primer usuario será ADMIN
                rol = 'ADMIN' if users_synced == 0 else 'ENCARGADO'
            
            # Crear nombre a partir del email
            nombre = user.display_name if user.display_name else user.email.split('@')[0].replace('.', ' ').title()
            
            # Datos del usuario para Supabase
            user_data = {
                'firebase_uid': user.uid,
                'email': user.email,
                'nombre': nombre,
                'rol': rol,
                'activo': not user.disabled,
                'sucursal_id': None  # Se puede asignar después
            }
            
            print(f"  Nombre: {nombre}")
            print(f"  Rol: {rol}")
            print(f"  Activo: {not user.disabled}")
            
            # Verificar si el usuario ya existe en Supabase
            check_response = requests.get(
                f'{SUPABASE_URL}/rest/v1/usuarios?firebase_uid=eq.{user.uid}',
                headers=headers
            )
            
            if check_response.status_code == 200 and len(check_response.json()) > 0:
                print(f"  ⚠️  Usuario ya existe en Supabase, actualizando...")
                existing_id = check_response.json()[0]['id']
                
                # Actualizar usuario existente
                update_response = requests.patch(
                    f'{SUPABASE_URL}/rest/v1/usuarios?id=eq.{existing_id}',
                    headers=headers,
                    json=user_data
                )
                
                if update_response.status_code in [200, 204]:
                    print(f"  ✅ Usuario actualizado exitosamente")
                    users_synced += 1
                else:
                    print(f"  ❌ Error al actualizar: {update_response.status_code}")
                    print(f"     {update_response.text}")
            else:
                # Insertar nuevo usuario
                insert_response = requests.post(
                    f'{SUPABASE_URL}/rest/v1/usuarios',
                    headers=headers,
                    json=user_data
                )
                
                if insert_response.status_code in [200, 201]:
                    print(f"  ✅ Usuario creado exitosamente en Supabase")
                    users_synced += 1
                else:
                    print(f"  ❌ Error al crear: {insert_response.status_code}")
                    print(f"     {insert_response.text}")
            
            print("-" * 80)
        
        # Obtener siguiente página
        page = page.get_next_page()
    
    print(f"\n✅ Sincronización completada: {users_synced} usuarios procesados")
    print("="*80 + "\n")
    
    # Verificar usuarios en Supabase
    print("\nVerificando usuarios en Supabase...")
    verify_response = requests.get(
        f'{SUPABASE_URL}/rest/v1/usuarios?select=*',
        headers=headers
    )
    
    if verify_response.status_code == 200:
        users = verify_response.json()
        print(f"\nTotal de usuarios en Supabase: {len(users)}")
        for user in users:
            print(f"  - {user['email']} ({user['rol']}) - Activo: {user['activo']}")
    
except Exception as e:
    print(f"\n❌ Error: {str(e)}")
    import traceback
    traceback.print_exc()
