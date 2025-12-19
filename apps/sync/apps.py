from django.apps import AppConfig
import threading
import logging

logger = logging.getLogger(__name__)

class SyncConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.sync'
    
    def ready(self):
        """
        Se ejecuta cuando Django está listo.
        Inicia el servicio de sincronización en segundo plano.
        """
        # Solo iniciar en el proceso principal (no en migraciones, etc.)
        import os
        import sys
        
        # Verificar que no sea un comando de migración o similar
        if (os.environ.get('RUN_MAIN') == 'true' or 
            'runserver' in sys.argv):
            self.start_sync_service()
    
    def start_sync_service(self):
        """Inicia el servicio de sincronización en un hilo separado"""
        try:
            from .sync_service import start_sync_service
            
            # Crear hilo para el servicio de sincronización
            sync_thread = threading.Thread(
                target=start_sync_service,
                daemon=True,  # Se cierra cuando Django se cierra
                name='firebase-sync'
            )
            sync_thread.start()
            
            logger.info("🔄 Servicio de sincronización iniciado en segundo plano")
            
        except Exception as e:
            logger.error(f"❌ Error iniciando servicio de sincronización: {e}")