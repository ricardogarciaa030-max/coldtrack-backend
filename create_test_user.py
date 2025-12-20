#!/usr/bin/env python3
"""
Script para crear un usuario de prueba en Firebase Auth
"""

import os
import sys
import django
from pathlib import Path

# Configurar Django
BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'coldtrack.settings')
django.setup()

import firebase_admin
from firebase_admin import credentials, auth
from django.conf import settings
import requests

def create_test_user():
    """Crear usuario de prueba en Firebase Auth"""
    try:
        # Inicializar Firebase Admin SDK
        try:
            firebase_admin.get_app()
        except ValueError:
            # Firebase no está inicializado
            private_key = settings.FIREBASE_PRIVATE_KEY.replace('\\n', '\n')
            
            cred_dict = {
                "type": "service_account",
                "project_id": settings.FIREBASE_PROJECT_ID,
                "private_key_id": "firebase-key-id",
                "private_key": private_key,
                "client_email": settings.FIREBASE_CLIENT_EMAIL,
                "client_id": "firebase-client-id",
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "client_x509_cert_url": f"https://www.googleapis.com/robot/v1/metadata/x509/{settings.FIREBASE_CLIENT_EMAIL}"
            }
            
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred)
        
        # Datos del usuario de prueba
        email = "admin@coldtrack.com"
        password = "123456789"
        display_name = "Administrador ColdTrack"
        
        print(f"🔥 Creando usuario en Firebase Auth...")
        print(f"📧 Email: {email}")
        print(f"🔑 Password: {password}")
        
        # Crear usuario en Firebase Auth
        user = auth.create_user(
            email=email,
            password=password,
            display_name=display_name,
            email_verified=True
        )
        
        print(f"✅ Usuario creado exitosamente!")
        print(f"🆔 UID: {user.uid}")
        
        # Ahora crear el usuario en Supabase
        config = settings.SUPABASE_CONFIG
        headers = {
            'apikey': config['service_key'],
            'Authorization': f'Bearer {config["service_key"]}',
            'Content-Type': 'application/json',
            'Prefer': 'return=representation'
        }
        
        user_data = {
            'firebase_uid': user.uid,
            'email': email,
            'nombre': display_name,
            'rol': 'ADMIN',
            'activo': True,
            'sucursal_id': 1
        }
        
        print(f"💾 Creando usuario en Supabase...")
        
        create_url = f'{config["url"]}/rest/v1/usuarios'
        response = requests.post(create_url, json=user_data, headers=headers)
        
        if response.status_code in [200, 201]:
            print(f"✅ Usuario sincronizado en Supabase!")
            print(f"📊 Datos: {response.json()}")
        else:
            print(f"❌ Error al sincronizar en Supabase: {response.status_code}")
            print(f"📄 Respuesta: {response.text}")
        
        print(f"\n🎉 ¡Usuario listo para usar!")
        print(f"🌐 Puedes hacer login con:")
        print(f"   📧 Email: {email}")
        print(f"   🔑 Password: {password}")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    create_test_user()