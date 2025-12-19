"""
ColdTrack URL Configuration

Este archivo define todas las rutas principales del proyecto.
Cada app tiene su propio archivo urls.py que se incluye aquí.
"""

from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import requests
from datetime import date, datetime, timedelta

def api_root(request):
    """Vista raíz de la API"""
    return JsonResponse({
        'message': 'ColdTrack API funcionando correctamente',
        'version': '1.0.0',
        'endpoints': {
            'auth': '/api/auth/',
            'users': '/api/users/',
            'sucursales': '/api/sucursales/',
            'camaras': '/api/camaras/',
            'dashboard': '/api/dashboard/',
            'eventos': '/api/eventos/'
        }
    })

@csrf_exempt
def test_kpis_direct(request):
    """Vista de KPIs directa para testing"""
    try:
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
        
        # 4. Cámaras con eventos en las últimas 24h
        hace_24h = (datetime.now() - timedelta(hours=24)).isoformat()
        eventos_24h_response = requests.get(
            f'{config["url"]}/rest/v1/eventos_temperatura?select=camara_id&fecha_inicio=gte.{hace_24h}',
            headers=headers
        )
        
        # Contar cámaras únicas con eventos
        camaras_con_eventos = set()
        if eventos_24h_response.status_code == 200:
            eventos_24h = eventos_24h_response.json()
            for evento in eventos_24h:
                camaras_con_eventos.add(evento['camara_id'])
        
        camaras_con_eventos_24h = len(camaras_con_eventos)
        
        return JsonResponse({
            'camaras_activas': camaras_activas,
            'sucursales_activas': sucursales_activas,
            'eventos_hoy': eventos_hoy,
            'camaras_con_eventos_24h': camaras_con_eventos_24h,
            'status': 'success',
            'message': 'KPIs calculados correctamente'
        })
        
    except Exception as e:
        return JsonResponse({
            'error': str(e),
            'status': 'error'
        })

@csrf_exempt
def usuarios_simple(request):
    """Vista de usuarios simple"""
    try:
        from django.conf import settings
        config = settings.SUPABASE_CONFIG
        
        headers = {
            'apikey': config['service_key'],
            'Authorization': f'Bearer {config["service_key"]}',
            'Content-Type': 'application/json'
        }
        
        response = requests.get(
            f'{config["url"]}/rest/v1/usuarios?select=*',
            headers=headers
        )
        
        if response.status_code == 200:
            return JsonResponse(response.json(), safe=False)
        else:
            return JsonResponse([])
            
    except Exception as e:
        return JsonResponse([])

@csrf_exempt
def eventos_recientes_simple(request):
    """Vista de eventos recientes simple"""
    try:
        from django.conf import settings
        config = settings.SUPABASE_CONFIG
        
        headers = {
            'apikey': config['service_key'],
            'Authorization': f'Bearer {config["service_key"]}',
            'Content-Type': 'application/json'
        }
        
        # Obtener eventos simples primero
        response = requests.get(
            f'{config["url"]}/rest/v1/eventos_temperatura?select=*&order=fecha_inicio.desc&limit=10',
            headers=headers
        )
        
        if response.status_code == 200:
            eventos = response.json()
            # Formatear datos para el frontend
            eventos_formateados = []
            for evento in eventos:
                eventos_formateados.append({
                    'id': evento['id'],
                    'tipo': evento['tipo'],
                    'estado': evento['estado'],
                    'fecha_inicio': evento['fecha_inicio'],
                    'fecha_fin': evento.get('fecha_fin'),
                    'temp_max_c': evento.get('temp_max_c', 0),
                    'camara': {
                        'nombre': 'Cámara Principal'  # Simplificado por ahora
                    },
                    'sucursal': {
                        'nombre': 'CarnesKar_O´higgins'  # Simplificado por ahora
                    }
                })
            
            return JsonResponse(eventos_formateados, safe=False)
        else:
            return JsonResponse([])
            
    except Exception as e:
        return JsonResponse([])

@csrf_exempt
def eventos_por_dia_simple(request):
    """Vista de eventos por día simple"""
    try:
        from django.conf import settings
        config = settings.SUPABASE_CONFIG
        
        headers = {
            'apikey': config['service_key'],
            'Authorization': f'Bearer {config["service_key"]}',
            'Content-Type': 'application/json'
        }
        
        # Últimos 7 días
        hace_7_dias = (datetime.now() - timedelta(days=7)).date()
        
        response = requests.get(
            f'{config["url"]}/rest/v1/eventos_temperatura?select=fecha_inicio&fecha_inicio=gte.{hace_7_dias}T00:00:00',
            headers=headers
        )
        
        if response.status_code == 200:
            eventos = response.json()
            
            # Agrupar por fecha
            eventos_por_fecha = {}
            for evento in eventos:
                fecha_str = evento['fecha_inicio'][:10]  # YYYY-MM-DD
                if fecha_str not in eventos_por_fecha:
                    eventos_por_fecha[fecha_str] = 0
                eventos_por_fecha[fecha_str] += 1
            
            # Crear lista de últimos 7 días
            resultado = []
            for i in range(7):
                fecha = hace_7_dias + timedelta(days=i)
                fecha_str = fecha.isoformat()
                resultado.append({
                    'fecha': fecha_str,
                    'total': eventos_por_fecha.get(fecha_str, 0)
                })
            
            return JsonResponse(resultado, safe=False)
        else:
            return JsonResponse([])
            
    except Exception as e:
        return JsonResponse([])

@csrf_exempt
def buscar_eventos_historicos(request):
    """Vista para búsqueda de eventos históricos con filtros de fecha"""
    try:
        from django.conf import settings
        config = settings.SUPABASE_CONFIG
        
        headers = {
            'apikey': config['service_key'],
            'Authorization': f'Bearer {config["service_key"]}',
            'Content-Type': 'application/json'
        }
        
        # Obtener parámetros de fecha (pueden venir por GET o POST)
        if request.method == 'POST':
            import json
            data = json.loads(request.body)
            fecha_inicio = data.get('fecha_inicio') or data.get('fecha_desde')
            fecha_fin = data.get('fecha_fin') or data.get('fecha_hasta')
        else:
            fecha_inicio = request.GET.get('fecha_inicio') or request.GET.get('fecha_desde')
            fecha_fin = request.GET.get('fecha_fin') or request.GET.get('fecha_hasta')
        
        # Si no hay fechas, usar últimos 30 días
        if not fecha_inicio or not fecha_fin:
            fecha_fin = datetime.now().date()
            fecha_inicio = fecha_fin - timedelta(days=30)
        else:
            # Convertir strings a fechas
            if isinstance(fecha_inicio, str):
                fecha_inicio = datetime.strptime(fecha_inicio, '%Y-%m-%d').date()
            if isinstance(fecha_fin, str):
                fecha_fin = datetime.strptime(fecha_fin, '%Y-%m-%d').date()
        
        # Construir query para Supabase
        query_url = f'{config["url"]}/rest/v1/eventos_temperatura?select=*&fecha_inicio=gte.{fecha_inicio}T00:00:00&fecha_inicio=lte.{fecha_fin}T23:59:59&order=fecha_inicio.desc'
        
        response = requests.get(query_url, headers=headers)
        
        if response.status_code == 200:
            eventos = response.json()
            
            # Formatear eventos para el frontend
            eventos_formateados = []
            for evento in eventos:
                # Calcular duración si no está disponible
                duracion_minutos = evento.get('duracion_minutos', 0)
                if not duracion_minutos and evento.get('fecha_fin'):
                    try:
                        inicio = datetime.fromisoformat(evento['fecha_inicio'].replace('Z', '+00:00'))
                        fin = datetime.fromisoformat(evento['fecha_fin'].replace('Z', '+00:00'))
                        duracion_minutos = int((fin - inicio).total_seconds() / 60)
                    except:
                        duracion_minutos = 0
                
                eventos_formateados.append({
                    'id': evento['id'],
                    'tipo': evento['tipo'],
                    'estado': evento['estado'],
                    'fecha_inicio': evento['fecha_inicio'],
                    'fecha_fin': evento.get('fecha_fin'),
                    'duracion_minutos': duracion_minutos,
                    'temp_max_c': float(evento.get('temp_max_c', 0)),
                    'camara': {
                        'nombre': 'Cámara Principal'  # Simplificado
                    },
                    'sucursal': {
                        'nombre': 'CarnesKar_O´higgins'  # Simplificado
                    }
                })
            
            return JsonResponse({
                'results': eventos_formateados,
                'count': len(eventos_formateados),
                'fecha_inicio': fecha_inicio.isoformat(),
                'fecha_fin': fecha_fin.isoformat()
            })
        else:
            return JsonResponse({
                'eventos': [],
                'total': 0,
                'error': f'Error en consulta: {response.status_code}'
            })
            
    except Exception as e:
        return JsonResponse({
            'results': [],
            'count': 0,
            'error': str(e)
        })

urlpatterns = [
    # API Root
    path('', api_root, name='api-root'),
    path('api/', api_root, name='api-root-with-prefix'),
    
    # Django Admin
    path('admin/', admin.site.urls),
    
    # Endpoints directos que funcionan
    path('api/test-kpis/', test_kpis_direct, name='test-kpis-direct'),
    path('api/dashboard/kpis/', test_kpis_direct, name='dashboard-kpis-working'),
    # path('api/users/', usuarios_simple, name='users-simple'),  # Comentado para usar ViewSet
    path('api/dashboard/eventos-recientes/', eventos_recientes_simple, name='eventos-recientes-working'),
    path('api/dashboard/eventos-por-dia/', eventos_por_dia_simple, name='eventos-por-dia-working'),
    path('api/eventos/buscar/', buscar_eventos_historicos, name='buscar-eventos-historicos'),
    path('api/eventos/', buscar_eventos_historicos, name='eventos-list'),  # Endpoint principal para el frontend
    
    # API Endpoints originales
    path('api/auth/', include('apps.auth.urls')),
    path('api/users/', include('apps.users.urls')),  # ViewSet de usuarios
    path('api/sucursales/', include('apps.sucursales.urls')),
    path('api/camaras/', include('apps.camaras.urls')),
    path('api/lecturas/', include('apps.lecturas.urls')),
    path('api/dashboard/', include('apps.dashboard.urls')),
    path('api/sync/', include('apps.sync.urls')),
]
