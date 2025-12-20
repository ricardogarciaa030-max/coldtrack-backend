"""
Comando para sincronización automática de usuarios Firebase -> Supabase
Se ejecuta periódicamente para mantener sincronizados los usuarios
"""

from django.core.management.base import BaseCommand
from django.conf import settings
import firebase_admin
from firebase_admin import credentials, auth
import requests
import logging
import time

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Sincroniza automáticamente usuarios de Firebase Auth a Supabase'

    def add_arguments(self, parser):
        parser.add_argument(
            '--interval',
            type=int,
            default=3600,  # 1 hora por defecto
            help='Intervalo en segundos entre sincronizaciones (default: 3600 = 1 hora)'
        )
        parser.add_argument(
            '--once',
            action='store_true',
            help='Ejecutar solo una vez en lugar de en bucle'
        )

    def handle(self, *args, **options):
        interval = options['interval']
        run_once = options['once']
        
        self.stdout.write(
            self.style.SUCCESS(f'🔄 Iniciando sincronización automática de usuarios')
        )
        
        if run_once:
            self.stdout.write(f'📅 Modo: Ejecución única')
            self.sync_users()
        else:
            self.stdout.write(f'🔁 Modo: Continuo cada {interval} segundos ({interval/3600:.1f} horas)')
            
            while True:
                try:
                    self.sync_users()
                    self.stdout.write(f'⏰ Próxima sincronización en {interval} segundos...')
                    time.sleep(interval)
                except KeyboardInterrupt:
                    self.stdout.write(self.style.WARNING('🛑 Sincronización detenida por usuario'))
                    break
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'❌ Error en sincronización: {str(e)}')
                    )
                    self.stdout.write(f'⏰ Reintentando en {interval} segundos...')
                    time.sleep(interval)

    def sync_users(self):
        """Ejecuta la sincronización de usuarios"""
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
            
            config = settings.SUPABASE_CONFIG
            headers = {
                'apikey': config['service_key'],
                'Authorization': f'Bearer {config["service_key"]}',
                'Content-Type': 'application/json',
                'Prefer': 'return=representation'
            }
            
            # Obtener todos los usuarios de Firebase
            page = auth.list_users()
            users_synced = 0
            users_found = 0
            users_updated = 0
            
            while page:
                for user in page.users:
                    users_found += 1
                    
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
                                    self.stdout.write(f'🔄 Usuario actualizado: {user.email}')
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
                                self.stdout.write(f'✅ Usuario sincronizado: {user.email}')
                
                # Siguiente página
                page = page.get_next_page()
            
            # Resumen
            self.stdout.write(
                self.style.SUCCESS(
                    f'🎉 Sincronización completada: '
                    f'{users_found} usuarios en Firebase, '
                    f'{users_synced} nuevos sincronizados, '
                    f'{users_updated} actualizados'
                )
            )
            
            return {
                'users_found': users_found,
                'users_synced': users_synced,
                'users_updated': users_updated
            }
            
        except Exception as e:
            error_msg = f'Error en sincronización: {str(e)}'
            self.stdout.write(self.style.ERROR(f'❌ {error_msg}'))
            logger.error(error_msg)
            raise e