from django.apps import AppConfig
import threading
import logging
import os

logger = logging.getLogger(__name__)

class SyncConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.sync'
    sync_started = False  # Variable de clase para evitar múltiples inicios
    
    def ready(self):
        """
        Se ejecuta cuando Django está listo.
        Inicia el servicio de sincronización en segundo plano.
        """
        # Solo iniciar una vez y en el proceso principal
        if SyncConfig.sync_started:
            return
        
        # Verificar que no sea un comando de migración o similar
        import sys
        if any(cmd in sys.argv for cmd in ['migrate', 'makemigrations', 'collectstatic', 'createsuperuser']):
            logger.info("⏭️ Saltando inicio de sincronización (comando de Django)")
            return
        
        # Solo iniciar en producción o si está explícitamente habilitado
        if os.environ.get('RUN_MAIN') == 'true' or os.environ.get('RENDER'):
            SyncConfig.sync_started = True
            self.start_sync_service()
    
    def start_sync_service(self):
        """Inicia el servicio de sincronización en un hilo separado"""
        try:
            from .sync_service import start_sync_service
            
            logger.info("🚀 Iniciando servicio de sincronización automática...")
            
            # Crear hilo para el servicio de sincronización
            sync_thread = threading.Thread(
                target=start_sync_service,
                daemon=True,  # Se cierra cuando Django se cierra
                name='firebase-sync-auto'
            )
            sync_thread.start()
            
            logger.info(f"✅ Servicio de sincronización iniciado en hilo: {sync_thread.name}")
            
        except Exception as e:
            logger.error(f"❌ Error iniciando servicio de sincronización: {e}")
            import traceback
            traceback.print_exc()