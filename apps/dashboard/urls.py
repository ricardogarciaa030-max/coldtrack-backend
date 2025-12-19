"""URLs del módulo de dashboard"""

from django.urls import path
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from . import views
import os
import requests
from datetime import date, datetime, timedelta

def simple_test(request):
    """Vista de prueba simple sin DRF"""
    return JsonResponse({'status': 'ok', 'message': 'Simple Django view works'})

@csrf_exempt
def simple_kpis(request):
    """Vista de KPIs simple sin DRF"""
    try:
        # Cargar configuración de Supabase
        from django.conf import settings
        config = settings.SUPABASE_CONFIG
        
        headers = {
            'apikey': config['service_key'],
            'Authorization': f'Bearer {config["service_key"]}',
            'Content-Type': 'application/json'
        }
        
        # 1. Cámaras activas
        camaras_response = requests.get(
            f'{config["url"]}/rest/v1/camaras_frio?select=id&activa=eq.true',
            headers=headers
        )
        camaras_activas = len(camaras_response.json()) if camaras_response.status_code == 200 else 0
        
        # 2. Sucursales activas
        sucursales_response = requests.get(
            f'{config["url"]}/rest/v1/sucursales?select=id&activa=eq.true',
            headers=headers
        )
        sucursales_activas = len(sucursales_response.json()) if sucursales_response.status_code == 200 else 0
        
        # 3. Eventos de hoy
        hoy = date.today()
        eventos_response = requests.get(
            f'{config["url"]}/rest/v1/eventos_temperatura?select=id&fecha_inicio=gte.{hoy}T00:00:00&fecha_inicio=lt.{hoy}T23:59:59',
            headers=headers
        )
        eventos_hoy = len(eventos_response.json()) if eventos_response.status_code == 200 else 0
        
        # 4. Lecturas de temperatura (últimas 24h)
        hace_24h = (datetime.now() - timedelta(hours=24)).isoformat()
        lecturas_response = requests.get(
            f'{config["url"]}/rest/v1/lecturas_temperatura?select=id&timestamp=gte.{hace_24h}',
            headers=headers
        )
        lecturas_24h = len(lecturas_response.json()) if lecturas_response.status_code == 200 else 0
        
        return JsonResponse({
            'camaras_activas': camaras_activas,
            'sucursales_activas': sucursales_activas,
            'eventos_hoy': eventos_hoy,
            'lecturas_24h': lecturas_24h,
            'status': 'success'
        })
        
    except Exception as e:
        return JsonResponse({
            'error': str(e),
            'camaras_activas': 0,
            'sucursales_activas': 0,
            'eventos_hoy': 0,
            'lecturas_24h': 0,
            'status': 'error'
        })

urlpatterns = [
    path('simple-test/', simple_test, name='dashboard-simple-test'),
    path('simple-kpis/', simple_kpis, name='dashboard-simple-kpis'),
    path('kpis/', views.get_kpis, name='dashboard-kpis'),
    path('eventos-por-dia/', views.get_eventos_por_dia, name='eventos-por-dia'),
    path('eventos-recientes/', views.get_eventos_recientes, name='eventos-recientes'),
    path('resumen-semanal/', views.get_resumen_semanal, name='resumen-semanal'),
    path('analisis-ejecutivo/', views.get_analisis_ejecutivo, name='analisis-ejecutivo'),
    path('guardar-resumen-ejecutivo/', views.guardar_resumen_ejecutivo, name='guardar-resumen-ejecutivo'),
    path('resumenes-ejecutivos/', views.get_resumenes_ejecutivos, name='resumenes-ejecutivos'),
]
