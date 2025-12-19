"""
Management command para ejecutar la sincronización Firebase manualmente

Uso:
    python manage.py sync_firebase
"""

from django.core.management.base import BaseCommand
from apps.sync.sync_service import start_sync_service

class Command(BaseCommand):
    help = 'Inicia el servicio de sincronización Firebase → Supabase'
    
    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('🚀 Iniciando servicio de sincronización...')
        )
        
        try:
            start_sync_service()
        except KeyboardInterrupt:
            self.stdout.write(
                self.style.WARNING('\n🛑 Servicio detenido por el usuario')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error: {str(e)}')
            )