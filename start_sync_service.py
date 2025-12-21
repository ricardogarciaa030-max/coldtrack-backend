#!/usr/bin/env python3
"""
Script para iniciar el servicio de sincronización en producción
Se ejecuta como proceso separado en Render
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

# Importar después de configurar Django
from apps.sync.sync_service import start_sync_service
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

if __name__ == "__main__":
    logger.info("🚀 Iniciando servicio de sincronización desde script independiente")
    try:
        start_sync_service()
    except KeyboardInterrupt:
        logger.info("🛑 Servicio detenido por usuario")
    except Exception as e:
        logger.error(f"❌ Error en servicio: {str(e)}")
        import traceback
        traceback.print_exc()