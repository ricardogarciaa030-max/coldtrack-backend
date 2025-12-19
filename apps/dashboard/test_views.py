"""
Vista de prueba simple
"""
from django.http import JsonResponse
from services.supabase_service import get_supabase_client

def test_view(request):
    return JsonResponse({"message": "Test successful", "method": request.method})

def test_kpis(request):
    """Vista de prueba para KPIs sin REST Framework"""
    try:
        client = get_supabase_client(use_service_key=True)
        
        # Obtener cámaras activas
        camaras_response = client.table('camaras_frio').select('id').eq('activa', True).execute()
        camaras_activas = len(camaras_response.data) if camaras_response.data else 0
        
        # Obtener sucursales activas
        sucursales_response = client.table('sucursales').select('id').eq('activa', True).execute()
        sucursales_activas = len(sucursales_response.data) if sucursales_response.data else 0
        
        # Obtener eventos de hoy (simplificado)
        from datetime import date
        hoy = date.today()
        eventos_response = client.table('eventos_temperatura')\
            .select('id')\
            .gte('fecha_inicio', f'{hoy}T00:00:00')\
            .lt('fecha_inicio', f'{hoy}T23:59:59')\
            .execute()
        eventos_hoy = len(eventos_response.data) if eventos_response.data else 0
        
        return JsonResponse({
            'camaras_activas': camaras_activas,
            'sucursales_activas': sucursales_activas,
            'eventos_hoy': eventos_hoy,
            'camaras_con_eventos_24h': 0  # Simplificado por ahora
        })
        
    except Exception as e:
        return JsonResponse({
            'error': str(e),
            'camaras_activas': 0,
            'sucursales_activas': 0,
            'eventos_hoy': 0,
            'camaras_con_eventos_24h': 0
        })