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

def test_auth_flow(request):
    """Test completo del flujo de autenticación"""
    try:
        from django.conf import settings
        import requests
        
        # 1. Verificar configuración de Firebase
        firebase_config = {
            'project_id': getattr(settings, 'FIREBASE_PROJECT_ID', 'NO_CONFIG'),
            'client_email': getattr(settings, 'FIREBASE_CLIENT_EMAIL', 'NO_CONFIG'),
            'has_private_key': bool(getattr(settings, 'FIREBASE_PRIVATE_KEY', '')),
            'database_url': getattr(settings, 'FIREBASE_DATABASE_URL', 'NO_CONFIG'),
        }
        
        # 2. Verificar conexión a Supabase
        config = settings.SUPABASE_CONFIG
        headers = {
            'apikey': config['service_key'],
            'Authorization': f'Bearer {config["service_key"]}',
            'Content-Type': 'application/json'
        }
        
        # Contar usuarios en Supabase
        users_url = f'{config["url"]}/rest/v1/usuarios?select=*'
        users_response = requests.get(users_url, headers=headers)
        
        supabase_status = {
            'connection': users_response.status_code == 200,
            'users_count': len(users_response.json()) if users_response.status_code == 200 else 0,
            'users': users_response.json() if users_response.status_code == 200 else []
        }
        
        # 3. Verificar inicialización de Firebase
        firebase_status = 'NOT_INITIALIZED'
        try:
            from services.firebase_service import initialize_firebase
            if initialize_firebase():
                firebase_status = 'INITIALIZED'
            else:
                firebase_status = 'FAILED_TO_INITIALIZE'
        except Exception as e:
            firebase_status = f'ERROR: {str(e)}'
        
        return JsonResponse({
            'message': 'Test de flujo de autenticación',
            'firebase_config': firebase_config,
            'firebase_status': firebase_status,
            'supabase_status': supabase_status,
            'cors_origins': getattr(settings, 'CORS_ALLOWED_ORIGINS', []),
            'debug_mode': settings.DEBUG
        })
        
    except Exception as e:
        return JsonResponse({
            'error': str(e),
            'message': 'Error en test de autenticación'
        })

def sync_firebase_users(request):
    """Sincronizar usuarios de Firebase Auth a Supabase"""
    try:
        # Inicializar Firebase Admin SDK
        import firebase_admin
        from firebase_admin import credentials, auth
        from django.conf import settings
        import requests
        import json
        
        # Verificar si Firebase ya está inicializado
        try:
            firebase_admin.get_app()
        except ValueError:
            # Firebase no está inicializado, inicializarlo
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
        
        while page:
            for user in page.users:
                users_found += 1
                
                # Verificar si el usuario ya existe en Supabase
                check_url = f'{config["url"]}/rest/v1/usuarios?firebase_uid=eq.{user.uid}'
                check_response = requests.get(check_url, headers=headers)
                
                if check_response.status_code == 200 and len(check_response.json()) > 0:
                    continue  # Usuario ya existe
                
                # Crear usuario en Supabase
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
            
            # Siguiente página
            page = page.get_next_page()
        
        return JsonResponse({
            'message': f'Sincronización completada: {users_synced} usuarios sincronizados de {users_found} encontrados',
            'users_found': users_found,
            'users_synced': users_synced
        })
        
    except Exception as e:
        return JsonResponse({
            'error': str(e),
            'message': 'Error en sincronización de usuarios'
        })

def init_basic_data(request):
    """Inicializar datos básicos: sucursales y cámaras"""
    try:
        from django.conf import settings
        import requests
        
        config = settings.SUPABASE_CONFIG
        headers = {
            'apikey': config['service_key'],
            'Authorization': f'Bearer {config["service_key"]}',
            'Content-Type': 'application/json',
            'Prefer': 'return=representation'
        }
        
        results = []
        
        # 1. Crear sucursal por defecto
        sucursal_data = {
            'nombre': 'CarnesKar_O´higgins',
            'direccion': 'Av. O´Higgins 123, Santiago',
            'activa': True
        }
        
        # Verificar si ya existe
        check_url = f'{config["url"]}/rest/v1/sucursales?nombre=eq.CarnesKar_O´higgins'
        check_response = requests.get(check_url, headers=headers)
        
        if check_response.status_code == 200 and len(check_response.json()) == 0:
            create_url = f'{config["url"]}/rest/v1/sucursales'
            response = requests.post(create_url, json=sucursal_data, headers=headers)
            if response.status_code in [200, 201]:
                results.append("✅ Sucursal creada")
            else:
                results.append(f"❌ Error creando sucursal: {response.text}")
        else:
            results.append("✅ Sucursal ya existe")
        
        # 2. Obtener ID de sucursal
        sucursal_response = requests.get(check_url, headers=headers)
        if sucursal_response.status_code == 200 and len(sucursal_response.json()) > 0:
            sucursal_id = sucursal_response.json()[0]['id']
            
            # 3. Crear cámara por defecto
            camara_data = {
                'nombre': 'Cámara 1',
                'firebase_path': 'device_001',
                'sucursal_id': sucursal_id,
                'activa': True
            }
            
            # Verificar si ya existe
            check_camara_url = f'{config["url"]}/rest/v1/camaras_frio?nombre=eq.Cámara 1'
            check_camara_response = requests.get(check_camara_url, headers=headers)
            
            if check_camara_response.status_code == 200 and len(check_camara_response.json()) == 0:
                create_camara_url = f'{config["url"]}/rest/v1/camaras_frio'
                camara_response = requests.post(create_camara_url, json=camara_data, headers=headers)
                if camara_response.status_code in [200, 201]:
                    results.append("✅ Cámara creada")
                else:
                    results.append(f"❌ Error creando cámara: {camara_response.text}")
            else:
                results.append("✅ Cámara ya existe")
        
        return JsonResponse({
            'message': 'Inicialización de datos básicos completada',
            'results': results
        })
        
    except Exception as e:
        return JsonResponse({
            'error': str(e),
            'message': 'Error en inicialización de datos básicos'
        })

def test_supabase_connection(request):
    """Probar conexión a Supabase y mostrar datos existentes"""
    try:
        from django.conf import settings
        import requests
        
        config = settings.SUPABASE_CONFIG
        headers = {
            'apikey': config['service_key'],
            'Authorization': f'Bearer {config["service_key"]}',
            'Content-Type': 'application/json'
        }
        
        results = {}
        
        # 1. Probar conexión básica
        test_url = f'{config["url"]}/rest/v1/'
        test_response = requests.get(test_url, headers=headers)
        results['connection'] = f"Status: {test_response.status_code}"
        
        # 2. Contar usuarios
        users_url = f'{config["url"]}/rest/v1/usuarios?select=count'
        users_response = requests.get(users_url, headers=headers)
        if users_response.status_code == 200:
            results['usuarios'] = f"Encontrados: {len(users_response.json())} usuarios"
        else:
            results['usuarios'] = f"Error: {users_response.status_code} - {users_response.text}"
        
        # 3. Contar sucursales
        sucursales_url = f'{config["url"]}/rest/v1/sucursales?select=*'
        sucursales_response = requests.get(sucursales_url, headers=headers)
        if sucursales_response.status_code == 200:
            sucursales = sucursales_response.json()
            results['sucursales'] = f"Encontradas: {len(sucursales)} sucursales"
            if sucursales:
                results['sucursales_list'] = [s['nombre'] for s in sucursales]
        else:
            results['sucursales'] = f"Error: {sucursales_response.status_code} - {sucursales_response.text}"
        
        # 4. Contar cámaras
        camaras_url = f'{config["url"]}/rest/v1/camaras_frio?select=*'
        camaras_response = requests.get(camaras_url, headers=headers)
        if camaras_response.status_code == 200:
            camaras = camaras_response.json()
            results['camaras'] = f"Encontradas: {len(camaras)} cámaras"
            if camaras:
                results['camaras_list'] = [c['nombre'] for c in camaras]
        else:
            results['camaras'] = f"Error: {camaras_response.status_code} - {camaras_response.text}"
        
        # 5. Configuración actual
        results['config'] = {
            'supabase_url': config['url'],
            'has_service_key': bool(config.get('service_key'))
        }
        
        return JsonResponse({
            'message': 'Test de conexión a Supabase',
            'results': results
        })
        
    except Exception as e:
        return JsonResponse({
            'error': str(e),
            'message': 'Error en test de conexión a Supabase'
        })

urlpatterns = [
    # API Root
    path('', api_root, name='api-root'),
    path('api/', api_root, name='api-root-with-prefix'),
    
    # Test de flujo de autenticación
    path('api/test/auth/', test_auth_flow, name='test-auth-flow'),
    
    # Test de conexión a Supabase
    path('api/test/supabase/', test_supabase_connection, name='test-supabase'),
    
    # Sincronización de usuarios Firebase -> Supabase
    path('api/sync/users/', sync_firebase_users, name='sync-firebase-users'),
    
    # Inicializar datos básicos
    path('api/init/basic/', init_basic_data, name='init-basic-data'),
    
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
