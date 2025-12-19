"""
Script para sincronizar datos históricos de Firebase a Supabase

Uso:
    python sync_historical_data.py --start-date 2025-12-02 --end-date 2025-12-08
    python sync_historical_data.py --date 2025-12-05
"""

import os
import sys
import django
import argparse
from datetime import datetime, date, timedelta

# Configurar Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'coldtrack.settings')
django.setup()

from apps.sync.services import sync_all_devices
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def sync_date_range(start_date, end_date):
    """
    Sincroniza datos de un rango de fechas.
    
    Args:
        start_date: Fecha de inicio
        end_date: Fecha de fin
    """
    logger.info("="*80)
    logger.info("SINCRONIZACIÓN DE DATOS HISTÓRICOS")
    logger.info("="*80)
    logger.info(f"Rango: {start_date} a {end_date}")
    logger.info("="*80)
    
    current_date = start_date
    total_stats = {
        'dias_procesados': 0,
        'total_lecturas': 0,
        'total_eventos': 0,
        'total_resumenes': 0,
        'errores': 0
    }
    
    while current_date <= end_date:
        logger.info(f"\n{'='*80}")
        logger.info(f"Sincronizando: {current_date}")
        logger.info(f"{'='*80}")
        
        try:
            result = sync_all_devices(current_date)
            
            total_stats['dias_procesados'] += 1
            total_stats['total_lecturas'] += result.get('total_lecturas', 0)
            total_stats['total_eventos'] += result.get('total_eventos', 0)
            total_stats['total_resumenes'] += result.get('total_resumenes', 0)
            total_stats['errores'] += result.get('errores', 0)
            
            logger.info(f"✅ Día completado:")
            logger.info(f"   - Lecturas: {result.get('total_lecturas', 0)}")
            logger.info(f"   - Eventos: {result.get('total_eventos', 0)}")
            logger.info(f"   - Resúmenes: {result.get('total_resumenes', 0)}")
            logger.info(f"   - Errores: {result.get('errores', 0)}")
            
        except Exception as e:
            logger.error(f"❌ Error al sincronizar {current_date}: {str(e)}")
            total_stats['errores'] += 1
        
        current_date += timedelta(days=1)
    
    # Resumen final
    logger.info("\n" + "="*80)
    logger.info("RESUMEN FINAL")
    logger.info("="*80)
    logger.info(f"Días procesados: {total_stats['dias_procesados']}")
    logger.info(f"Total de lecturas: {total_stats['total_lecturas']}")
    logger.info(f"Total de eventos: {total_stats['total_eventos']}")
    logger.info(f"Total de resúmenes: {total_stats['total_resumenes']}")
    logger.info(f"Errores: {total_stats['errores']}")
    logger.info("="*80)


def main():
    parser = argparse.ArgumentParser(description='Sincronizar datos históricos de Firebase a Supabase')
    parser.add_argument('--start-date', type=str, help='Fecha de inicio (YYYY-MM-DD)')
    parser.add_argument('--end-date', type=str, help='Fecha de fin (YYYY-MM-DD)')
    parser.add_argument('--date', type=str, help='Fecha única a sincronizar (YYYY-MM-DD)')
    
    args = parser.parse_args()
    
    if args.date:
        # Sincronizar una sola fecha
        target_date = datetime.strptime(args.date, '%Y-%m-%d').date()
        sync_date_range(target_date, target_date)
    elif args.start_date and args.end_date:
        # Sincronizar rango de fechas
        start = datetime.strptime(args.start_date, '%Y-%m-%d').date()
        end = datetime.strptime(args.end_date, '%Y-%m-%d').date()
        sync_date_range(start, end)
    else:
        # Por defecto, sincronizar la última semana
        end_date = date.today()
        start_date = end_date - timedelta(days=7)
        logger.info("No se especificaron fechas, sincronizando última semana...")
        sync_date_range(start_date, end_date)


if __name__ == '__main__':
    main()
