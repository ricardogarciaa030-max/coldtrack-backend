"""
Vistas de Dashboard

Proporciona KPIs y estadísticas para el dashboard principal.
"""

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from datetime import datetime, timedelta, date
from services.supabase_service import get_supabase_client
import logging

logger = logging.getLogger(__name__)


def get_kpis(request):
    """
    Obtiene los KPIs principales del dashboard desde Supabase.
    
    GET /api/dashboard/kpis/
    
    Returns:
        {
            "camaras_activas": 15,
            "sucursales_activas": 3,
            "eventos_hoy": 5,
            "camaras_con_eventos_24h": 3
        }
    """
    from django.http import JsonResponse
    
    try:
        user = getattr(request, 'firebase_user', None)
        client = get_supabase_client(use_service_key=True)
        
        # Construir filtros según rol del usuario
        sucursal_filter = {}
        if user and user.get('rol') != 'ADMIN':
            sucursal_id = user.get('sucursal_id')
            if sucursal_id:
                sucursal_filter = {'sucursal_id': sucursal_id}
        
        # 1. Cámaras activas
        camaras_query = client.table('camaras_frio').select('id').eq('activa', True)
        if sucursal_filter:
            camaras_query = camaras_query.eq('sucursal_id', sucursal_filter['sucursal_id'])
        camaras_response = camaras_query.execute()
        camaras_activas = len(camaras_response.data) if camaras_response.data else 0
        
        # 2. Sucursales activas
        if user and user.get('rol') == 'ADMIN':
            sucursales_response = client.table('sucursales').select('id').eq('activa', True).execute()
            sucursales_activas = len(sucursales_response.data) if sucursales_response.data else 0
        else:
            sucursales_activas = 1
        
        # 3. Eventos de hoy
        hoy = date.today()
        eventos_hoy_query = client.table('eventos_temperatura')\
            .select('id')\
            .gte('fecha_inicio', f'{hoy}T00:00:00')\
            .lt('fecha_inicio', f'{hoy}T23:59:59')
        
        if sucursal_filter:
            # Necesitamos hacer JOIN con cámaras para filtrar por sucursal
            eventos_hoy_query = client.table('eventos_temperatura')\
                .select('id, camara_id, camaras_frio!inner(sucursal_id)')\
                .gte('fecha_inicio', f'{hoy}T00:00:00')\
                .lt('fecha_inicio', f'{hoy}T23:59:59')\
                .eq('camaras_frio.sucursal_id', sucursal_filter['sucursal_id'])
        
        eventos_hoy_response = eventos_hoy_query.execute()
        eventos_hoy = len(eventos_hoy_response.data) if eventos_hoy_response.data else 0
        
        # 4. Cámaras con eventos en las últimas 24h
        hace_24h = datetime.now() - timedelta(hours=24)
        eventos_24h_query = client.table('eventos_temperatura')\
            .select('camara_id')\
            .gte('fecha_inicio', hace_24h.isoformat())
        
        if sucursal_filter:
            eventos_24h_query = client.table('eventos_temperatura')\
                .select('camara_id, camaras_frio!inner(sucursal_id)')\
                .gte('fecha_inicio', hace_24h.isoformat())\
                .eq('camaras_frio.sucursal_id', sucursal_filter['sucursal_id'])
        
        eventos_24h_response = eventos_24h_query.execute()
        
        # Contar cámaras únicas
        camaras_con_eventos = set()
        if eventos_24h_response.data:
            for evento in eventos_24h_response.data:
                camaras_con_eventos.add(evento['camara_id'])
        
        return JsonResponse({
            'camaras_activas': camaras_activas,
            'sucursales_activas': sucursales_activas,
            'eventos_hoy': eventos_hoy,
            'camaras_con_eventos_24h': len(camaras_con_eventos)
        })
        
    except Exception as e:
        logger.error(f"Error al obtener KPIs: {str(e)}")
        return JsonResponse({
            'camaras_activas': 0,
            'sucursales_activas': 0,
            'eventos_hoy': 0,
            'camaras_con_eventos_24h': 0
        })


@api_view(['GET'])
@permission_classes([AllowAny])
def get_eventos_por_dia(request):
    """
    Obtiene la cantidad de eventos por día (últimos 7 días) desde Supabase.
    
    GET /api/dashboard/eventos-por-dia/
    
    Returns:
        [
            {"fecha": "2025-12-01", "total": 5},
            {"fecha": "2025-12-02", "total": 3},
            ...
        ]
    """
    try:
        user = request.firebase_user
        client = get_supabase_client(use_service_key=True)
        
        # Últimos 7 días
        hace_7_dias = date.today() - timedelta(days=7)
        
        # Obtener eventos de los últimos 7 días
        eventos_query = client.table('eventos_temperatura')\
            .select('fecha_inicio, camara_id')\
            .gte('fecha_inicio', hace_7_dias.isoformat())
        
        # Filtrar por sucursal si no es ADMIN
        if user and user.get('rol') != 'ADMIN':
            sucursal_id = user.get('sucursal_id')
            if sucursal_id:
                eventos_query = client.table('eventos_temperatura')\
                    .select('fecha_inicio, camara_id, camaras_frio!inner(sucursal_id)')\
                    .gte('fecha_inicio', hace_7_dias.isoformat())\
                    .eq('camaras_frio.sucursal_id', sucursal_id)
        
        eventos_response = eventos_query.execute()
        
        # Agrupar por fecha
        eventos_por_fecha = {}
        if eventos_response.data:
            for evento in eventos_response.data:
                fecha_str = evento['fecha_inicio'][:10]  # YYYY-MM-DD
                if fecha_str not in eventos_por_fecha:
                    eventos_por_fecha[fecha_str] = 0
                eventos_por_fecha[fecha_str] += 1
        
        # Convertir a lista ordenada
        resultado = []
        for i in range(7):
            fecha = hace_7_dias + timedelta(days=i)
            fecha_str = fecha.isoformat()
            resultado.append({
                'fecha': fecha_str,
                'total': eventos_por_fecha.get(fecha_str, 0)
            })
        
        return Response(resultado)
        
    except Exception as e:
        logger.error(f"Error al obtener eventos por día: {str(e)}")
        return Response([])


@api_view(['GET'])
@permission_classes([AllowAny])
def get_eventos_recientes(request):
    """
    Obtiene los últimos 10 eventos desde Supabase.
    
    GET /api/dashboard/eventos-recientes/
    
    Returns:
        Lista de eventos con información de cámara y sucursal
    """
    try:
        user = request.firebase_user
        client = get_supabase_client(use_service_key=True)
        
        # Obtener eventos recientes con JOIN
        eventos_query = client.table('eventos_temperatura')\
            .select('*, camaras_frio(id, nombre, sucursales(id, nombre))')\
            .order('fecha_inicio', desc=True)\
            .limit(10)
        
        # Filtrar por sucursal si no es ADMIN
        if user and user.get('rol') != 'ADMIN':
            sucursal_id = user.get('sucursal_id')
            if sucursal_id:
                eventos_query = eventos_query.eq('camaras_frio.sucursal_id', sucursal_id)
        
        eventos_response = eventos_query.execute()
        
        data = []
        if eventos_response.data:
            for evento in eventos_response.data:
                camara = evento.get('camaras_frio', {})
                sucursal = camara.get('sucursales', {}) if camara else {}
                
                data.append({
                    'id': evento['id'],
                    'tipo': evento['tipo'],
                    'estado': evento['estado'],
                    'fecha_inicio': evento['fecha_inicio'],
                    'fecha_fin': evento.get('fecha_fin'),
                    'temp_max_c': float(evento['temp_max_c']) if evento['temp_max_c'] else 0,
                    'camara': {
                        'id': camara.get('id', 0),
                        'nombre': camara.get('nombre', 'N/A'),
                    },
                    'sucursal': {
                        'id': sucursal.get('id', 0),
                        'nombre': sucursal.get('nombre', 'N/A'),
                    }
                })
        
        return Response(data)
        
    except Exception as e:
        logger.error(f"Error al obtener eventos recientes: {str(e)}")
        return Response([])


@api_view(['GET'])
@permission_classes([AllowAny])
def get_analisis_ejecutivo(request):
    """
    Vista ejecutiva para jefes de sucursal.
    Proporciona análisis empresarial, no técnico.
    
    GET /api/dashboard/analisis-ejecutivo/
    
    Parámetros:
        - fecha_inicio: Fecha de inicio del análisis
        - fecha_fin: Fecha de fin del análisis
        - camara_id: ID de cámara específica (opcional)
    
    Returns:
        Análisis completo con KPIs, comparaciones y rankings
    """
    try:
        user = getattr(request, 'firebase_user', None)
        client = get_supabase_client(use_service_key=True)
        
        # Obtener parámetros
        fecha_inicio = request.GET.get('fechaInicio')
        fecha_fin = request.GET.get('fechaFin')
        camara_id = request.GET.get('camaraId')
        
        # Fechas por defecto (últimos 30 días)
        if not fecha_inicio:
            fecha_inicio = (date.today() - timedelta(days=30)).isoformat()
        if not fecha_fin:
            fecha_fin = date.today().isoformat()
        
        # Filtros de sucursal
        sucursal_filter = {}
        if user and user.get('rol') != 'ADMIN':
            sucursal_id = user.get('sucursal_id')
            if sucursal_id:
                sucursal_filter = {'sucursal_id': sucursal_id}
        
        # 1️⃣ CALCULAR KPIs PRINCIPALES
        kpis = calcular_kpis_ejecutivos(client, fecha_inicio, fecha_fin, sucursal_filter, camara_id)
        
        # 2️⃣ COMPARACIÓN ADAPTATIVA (diaria, semanal o mensual)
        comparacion_adaptativa = obtener_comparacion_adaptativa(client, fecha_inicio, fecha_fin, sucursal_filter)
        
        # 3️⃣ TENDENCIA ADAPTATIVA (usa la misma lógica que comparación)
        tendencia_adaptativa = obtener_tendencia_adaptativa(client, fecha_inicio, fecha_fin, sucursal_filter)
        
        # 4️⃣ ANÁLISIS DE EVENTOS
        analisis_eventos = obtener_analisis_eventos(client, fecha_inicio, fecha_fin, sucursal_filter)
        
        # 5️⃣ TEMPERATURAS DIARIAS
        temperaturas = obtener_temperaturas_diarias(client, fecha_inicio, fecha_fin, sucursal_filter)
        
        # 6️⃣ RANKING DE CÁMARAS
        ranking_camaras = obtener_ranking_camaras(client, fecha_inicio, fecha_fin, sucursal_filter)
        
        return Response({
            'kpis': kpis,
            'comparacionAdaptativa': comparacion_adaptativa,
            'tendenciaAdaptativa': tendencia_adaptativa,
            'analisisEventos': analisis_eventos,
            'temperaturas': temperaturas,
            'rankingCamaras': ranking_camaras
        })
        
    except Exception as e:
        logger.error(f"Error en análisis ejecutivo: {str(e)}")
        return Response({
            'error': 'Error al generar análisis ejecutivo'
        }, status=500)


def calcular_kpis_ejecutivos(client, fecha_inicio, fecha_fin, sucursal_filter, camara_id=None):
    """Calcula los KPIs principales para la vista ejecutiva usando datos reales"""
    try:
        # 1. OBTENER LECTURAS DE TEMPERATURA (incluir todo el día final)
        fecha_fin_completa = f"{fecha_fin}T23:59:59"
        lecturas_query = client.table('lecturas_temperatura')\
            .select('temperatura_c, timestamp, camara_id')\
            .gte('timestamp', fecha_inicio)\
            .lte('timestamp', fecha_fin_completa)
        
        if camara_id and camara_id != 'todas':
            lecturas_query = lecturas_query.eq('camara_id', camara_id)
        
        lecturas_response = lecturas_query.execute()
        
        # Calcular temperatura promedio
        if lecturas_response.data:
            temperaturas = [float(l['temperatura_c']) for l in lecturas_response.data]
            temp_promedio = sum(temperaturas) / len(temperaturas)
        else:
            temp_promedio = 0
        
        # 2. OBTENER EVENTOS (incluir todo el día final)
        eventos_query = client.table('eventos_temperatura')\
            .select('tipo, duracion_minutos, camara_id')\
            .gte('fecha_inicio', fecha_inicio)\
            .lte('fecha_inicio', fecha_fin_completa)
        
        if camara_id and camara_id != 'todas':
            eventos_query = eventos_query.eq('camara_id', camara_id)
        
        eventos_response = eventos_query.execute()
        
        # Calcular métricas de eventos
        total_eventos = len(eventos_response.data) if eventos_response.data else 0
        horas_deshielo = 0
        horas_falla = 0
        
        if eventos_response.data:
            for evento in eventos_response.data:
                duracion_min = evento.get('duracion_minutos', 0) or 0
                duracion_horas = duracion_min / 60.0
                
                tipo = evento['tipo']
                if tipo in ['DESHIELO_N', 'DESHIELO_P']:
                    horas_deshielo += duracion_horas
                elif tipo in ['FALLA', 'FALLA_EN_CURSO']:
                    horas_falla += duracion_horas
        
        # Calcular porcentaje de tiempo normal
        dias_periodo = (datetime.fromisoformat(fecha_fin) - datetime.fromisoformat(fecha_inicio)).days + 1
        horas_total = dias_periodo * 24
        horas_problemas = horas_deshielo + horas_falla
        porcentaje_normal = ((horas_total - horas_problemas) / horas_total * 100) if horas_total > 0 else 100
        
        # 3. CALCULAR PERÍODO ANTERIOR PARA COMPARACIÓN
        fecha_inicio_anterior = (datetime.fromisoformat(fecha_inicio) - timedelta(days=dias_periodo)).isoformat()
        fecha_fin_anterior = fecha_inicio
        
        # Lecturas período anterior
        lecturas_anterior_query = client.table('lecturas_temperatura')\
            .select('temperatura_c')\
            .gte('timestamp', fecha_inicio_anterior)\
            .lt('timestamp', fecha_fin_anterior)
        
        if camara_id and camara_id != 'todas':
            lecturas_anterior_query = lecturas_anterior_query.eq('camara_id', camara_id)
        
        lecturas_anterior_response = lecturas_anterior_query.execute()
        
        if lecturas_anterior_response.data:
            temps_anteriores = [float(l['temperatura_c']) for l in lecturas_anterior_response.data]
            temp_promedio_anterior = sum(temps_anteriores) / len(temps_anteriores)
        else:
            temp_promedio_anterior = temp_promedio
        
        # Eventos período anterior
        eventos_anterior_query = client.table('eventos_temperatura')\
            .select('tipo, duracion_minutos')\
            .gte('fecha_inicio', fecha_inicio_anterior)\
            .lt('fecha_inicio', fecha_fin_anterior)
        
        if camara_id and camara_id != 'todas':
            eventos_anterior_query = eventos_anterior_query.eq('camara_id', camara_id)
        
        eventos_anterior_response = eventos_anterior_query.execute()
        
        total_eventos_anterior = len(eventos_anterior_response.data) if eventos_anterior_response.data else 0
        horas_deshielo_anterior = 0
        horas_falla_anterior = 0
        
        if eventos_anterior_response.data:
            for evento in eventos_anterior_response.data:
                duracion_min = evento.get('duracion_minutos', 0) or 0
                duracion_horas = duracion_min / 60.0
                
                tipo = evento['tipo']
                if tipo in ['DESHIELO_N', 'DESHIELO_P']:
                    horas_deshielo_anterior += duracion_horas
                elif tipo in ['FALLA', 'FALLA_EN_CURSO']:
                    horas_falla_anterior += duracion_horas
        
        horas_problemas_anterior = horas_deshielo_anterior + horas_falla_anterior
        porcentaje_normal_anterior = ((horas_total - horas_problemas_anterior) / horas_total * 100) if horas_total > 0 else 100
        
        # Calcular variaciones porcentuales
        def calcular_variacion(actual, anterior):
            if anterior == 0:
                return 0 if actual == 0 else 100
            return round(((actual - anterior) / anterior) * 100, 1)
        
        return {
            'temperaturaPromedio': round(temp_promedio, 1),
            'totalEventos': int(total_eventos),
            'horasDeshielo': round(horas_deshielo, 1),
            'horasFalla': round(horas_falla, 1),
            'porcentajeNormal': round(porcentaje_normal, 1),
            'variacionTemperatura': calcular_variacion(temp_promedio, temp_promedio_anterior),
            'variacionEventos': calcular_variacion(total_eventos, total_eventos_anterior),
            'variacionDeshielo': calcular_variacion(horas_deshielo, horas_deshielo_anterior),
            'variacionFalla': calcular_variacion(horas_falla, horas_falla_anterior),
            'variacionNormal': calcular_variacion(porcentaje_normal, porcentaje_normal_anterior)
        }
        
    except Exception as e:
        logger.error(f"Error calculando KPIs ejecutivos: {str(e)}")
        return {
            'temperaturaPromedio': 0,
            'totalEventos': 0,
            'horasDeshielo': 0,
            'horasFalla': 0,
            'porcentajeNormal': 100,
            'variacionTemperatura': 0,
            'variacionEventos': 0,
            'variacionDeshielo': 0,
            'variacionFalla': 0,
            'variacionNormal': 0
        }


def obtener_comparacion_adaptativa(client, fecha_inicio, fecha_fin, sucursal_filter):
    """Obtiene comparación adaptativa según el período seleccionado"""
    try:
        # Calcular días del período
        fecha_inicio_obj = datetime.fromisoformat(fecha_inicio)
        fecha_fin_obj = datetime.fromisoformat(fecha_fin)
        dias_periodo = (fecha_fin_obj - fecha_inicio_obj).days + 1
        
        logger.info(f"Período seleccionado: {dias_periodo} días")
        
        # Determinar tipo de comparación
        if dias_periodo <= 7:
            # COMPARACIÓN DIARIA (1-7 días)
            return obtener_comparacion_diaria(client, fecha_inicio, fecha_fin, sucursal_filter)
        elif dias_periodo <= 30:
            # COMPARACIÓN SEMANAL (8-30 días)
            return obtener_comparacion_semanal_adaptativa(client, fecha_inicio, fecha_fin, sucursal_filter)
        else:
            # COMPARACIÓN MENSUAL (31+ días)
            return obtener_comparacion_mensual_adaptativa(client, fecha_inicio, fecha_fin, sucursal_filter)
        
    except Exception as e:
        logger.error(f"Error en comparación adaptativa: {str(e)}")
        return {
            'tipo': 'error',
            'titulo': 'Error',
            'datos': []
        }


def obtener_comparacion_diaria(client, fecha_inicio, fecha_fin, sucursal_filter):
    """Comparación día por día"""
    try:
        from datetime import timedelta
        
        # Obtener eventos del período (incluir todo el día final)
        fecha_fin_completa = f"{fecha_fin}T23:59:59"
        eventos_query = client.table('eventos_temperatura')\
            .select('tipo, duracion_minutos, fecha_inicio')\
            .gte('fecha_inicio', fecha_inicio)\
            .lte('fecha_inicio', fecha_fin_completa)
        
        eventos_data = eventos_query.execute()
        
        # Obtener lecturas del período
        lecturas_query = client.table('lecturas_temperatura')\
            .select('temperatura_c, timestamp')\
            .gte('timestamp', fecha_inicio)\
            .lte('timestamp', fecha_fin_completa)
        
        lecturas_data = lecturas_query.execute()
        
        # Inicializar todos los días del rango con 0 eventos
        dias = {}
        fecha_actual = datetime.fromisoformat(fecha_inicio)
        fecha_final = datetime.fromisoformat(fecha_fin)
        
        while fecha_actual <= fecha_final:
            dia_key = fecha_actual.strftime('%Y-%m-%d')
            dia_nombre = fecha_actual.strftime('%d/%m')
            
            dias[dia_key] = {
                'periodo': dia_nombre,
                'eventos': 0,
                'horasFalla': 0,
                'tempPromedio': []
            }
            
            fecha_actual += timedelta(days=1)
        
        # Procesar eventos
        if eventos_data.data:
            for evento in eventos_data.data:
                fecha_obj = datetime.fromisoformat(evento['fecha_inicio'])
                dia_key = fecha_obj.strftime('%Y-%m-%d')
                
                if dia_key in dias:  # Solo si está en nuestro rango
                    dias[dia_key]['eventos'] += 1
                    
                    # Calcular horas de falla
                    if evento['tipo'] in ['FALLA', 'FALLA_EN_CURSO']:
                        duracion_min = evento.get('duracion_minutos', 0) or 0
                        dias[dia_key]['horasFalla'] += duracion_min / 60.0
        
        # Procesar lecturas
        if lecturas_data.data:
            for lectura in lecturas_data.data:
                fecha_obj = datetime.fromisoformat(lectura['timestamp'])
                dia_key = fecha_obj.strftime('%Y-%m-%d')
                
                if dia_key in dias:  # Solo si está en nuestro rango
                    dias[dia_key]['tempPromedio'].append(float(lectura['temperatura_c']))
        
        # Convertir a lista
        resultado = []
        for dia_data in dias.values():
            temp_prom = sum(dia_data['tempPromedio']) / len(dia_data['tempPromedio']) if dia_data['tempPromedio'] else 0
            resultado.append({
                'periodo': dia_data['periodo'],
                'eventos': dia_data['eventos'],
                'horasFalla': round(dia_data['horasFalla'], 1),
                'tempPromedio': round(temp_prom, 1)
            })
        
        resultado.sort(key=lambda x: x['periodo'])
        
        return {
            'tipo': 'diaria',
            'titulo': 'Comparación Diaria',
            'datos': resultado
        }
        
    except Exception as e:
        logger.error(f"Error en comparación diaria: {str(e)}")
        return {'tipo': 'diaria', 'titulo': 'Comparación Diaria', 'datos': []}


def obtener_comparacion_semanal_adaptativa(client, fecha_inicio, fecha_fin, sucursal_filter):
    """Comparación semana por semana"""
    try:
        # Usar la función común para calcular semanas
        return calcular_datos_semanales(client, fecha_inicio, fecha_fin, sucursal_filter, 'comparacion')
        
    except Exception as e:
        logger.error(f"Error en comparación semanal: {str(e)}")
        return {'tipo': 'semanal', 'titulo': 'Comparación Semanal', 'datos': []}


def obtener_comparacion_mensual_adaptativa(client, fecha_inicio, fecha_fin, sucursal_filter):
    """Comparación mes por mes"""
    try:
        # Obtener eventos del período (incluir todo el día final)
        fecha_fin_completa = f"{fecha_fin}T23:59:59"
        eventos_query = client.table('eventos_temperatura')\
            .select('tipo, duracion_minutos, fecha_inicio')\
            .gte('fecha_inicio', fecha_inicio)\
            .lte('fecha_inicio', fecha_fin_completa)
        
        eventos_data = eventos_query.execute()
        
        # Obtener lecturas del período
        lecturas_query = client.table('lecturas_temperatura')\
            .select('temperatura_c, timestamp')\
            .gte('timestamp', fecha_inicio)\
            .lte('timestamp', fecha_fin_completa)
        
        lecturas_data = lecturas_query.execute()
        
        # Agrupar por mes
        meses = {}
        
        # Procesar eventos
        if eventos_data.data:
            for evento in eventos_data.data:
                fecha_obj = datetime.fromisoformat(evento['fecha_inicio'])
                mes_key = fecha_obj.strftime('%Y-%m')
                mes_nombre = fecha_obj.strftime('%b %Y')
                
                if mes_key not in meses:
                    meses[mes_key] = {
                        'periodo': mes_nombre,
                        'eventos': 0,
                        'horasFalla': 0,
                        'tempPromedio': []
                    }
                
                meses[mes_key]['eventos'] += 1
                
                # Calcular horas de falla
                if evento['tipo'] in ['FALLA', 'FALLA_EN_CURSO']:
                    duracion_min = evento.get('duracion_minutos', 0) or 0
                    meses[mes_key]['horasFalla'] += duracion_min / 60.0
        
        # Procesar lecturas
        if lecturas_data.data:
            for lectura in lecturas_data.data:
                fecha_obj = datetime.fromisoformat(lectura['timestamp'])
                mes_key = fecha_obj.strftime('%Y-%m')
                mes_nombre = fecha_obj.strftime('%b %Y')
                
                if mes_key not in meses:
                    meses[mes_key] = {
                        'periodo': mes_nombre,
                        'eventos': 0,
                        'horasFalla': 0,
                        'tempPromedio': []
                    }
                
                meses[mes_key]['tempPromedio'].append(float(lectura['temperatura_c']))
        
        # Convertir a lista
        resultado = []
        for mes_data in meses.values():
            temp_prom = sum(mes_data['tempPromedio']) / len(mes_data['tempPromedio']) if mes_data['tempPromedio'] else 0
            resultado.append({
                'periodo': mes_data['periodo'],
                'eventos': mes_data['eventos'],
                'horasFalla': round(mes_data['horasFalla'], 1),
                'tempPromedio': round(temp_prom, 1)
            })
        
        resultado.sort(key=lambda x: x['periodo'])
        
        return {
            'tipo': 'mensual',
            'titulo': 'Comparación Mensual',
            'datos': resultado
        }
        
    except Exception as e:
        logger.error(f"Error en comparación mensual: {str(e)}")
        return {'tipo': 'mensual', 'titulo': 'Comparación Mensual', 'datos': []}


def obtener_tendencia_adaptativa(client, fecha_inicio, fecha_fin, sucursal_filter):
    """Obtiene tendencia adaptativa según el período seleccionado"""
    try:
        # Calcular días del período
        fecha_inicio_obj = datetime.fromisoformat(fecha_inicio)
        fecha_fin_obj = datetime.fromisoformat(fecha_fin)
        dias_periodo = (fecha_fin_obj - fecha_inicio_obj).days + 1
        
        logger.info(f"Tendencia adaptativa para período de {dias_periodo} días")
        
        # Determinar tipo de tendencia (misma lógica que comparación)
        if dias_periodo <= 7:
            # TENDENCIA DIARIA (1-7 días)
            return obtener_tendencia_diaria(client, fecha_inicio, fecha_fin, sucursal_filter)
        elif dias_periodo <= 30:
            # TENDENCIA SEMANAL (8-30 días)
            return obtener_tendencia_semanal_real(client, fecha_inicio, fecha_fin, sucursal_filter)
        else:
            # TENDENCIA MENSUAL (31+ días)
            return obtener_tendencia_mensual(client, fecha_inicio, fecha_fin, sucursal_filter)
        
    except Exception as e:
        logger.error(f"Error en tendencia adaptativa: {str(e)}")
        return {
            'tipo': 'error',
            'titulo': 'Error',
            'datos': []
        }


def obtener_tendencia_diaria(client, fecha_inicio, fecha_fin, sucursal_filter):
    """Tendencia día por día"""
    try:
        from datetime import timedelta
        
        # Obtener eventos del período
        fecha_fin_completa = f"{fecha_fin}T23:59:59"
        eventos_query = client.table('eventos_temperatura')\
            .select('tipo, duracion_minutos, fecha_inicio')\
            .gte('fecha_inicio', fecha_inicio)\
            .lte('fecha_inicio', fecha_fin_completa)
        
        eventos_data = eventos_query.execute()
        
        # Inicializar todos los días del rango
        dias = {}
        fecha_actual = datetime.fromisoformat(fecha_inicio)
        fecha_final = datetime.fromisoformat(fecha_fin)
        
        while fecha_actual <= fecha_final:
            dia_key = fecha_actual.strftime('%Y-%m-%d')
            dia_nombre = fecha_actual.strftime('%d/%m')
            
            dias[dia_key] = {
                'periodo': dia_nombre,
                'eventos': 0,
                'horasCriticas': 0
            }
            
            fecha_actual += timedelta(days=1)
        
        # Procesar eventos
        if eventos_data.data:
            for evento in eventos_data.data:
                fecha_obj = datetime.fromisoformat(evento['fecha_inicio'])
                dia_key = fecha_obj.strftime('%Y-%m-%d')
                
                if dia_key in dias:
                    dias[dia_key]['eventos'] += 1
                    
                    # Calcular horas críticas (deshielo + falla)
                    duracion_min = evento.get('duracion_minutos', 0) or 0
                    duracion_horas = duracion_min / 60.0
                    
                    tipo = evento['tipo']
                    if tipo in ['DESHIELO_N', 'DESHIELO_P', 'FALLA', 'FALLA_EN_CURSO']:
                        dias[dia_key]['horasCriticas'] += duracion_horas
        
        # Convertir a lista
        resultado = []
        for dia_data in dias.values():
            resultado.append({
                'periodo': dia_data['periodo'],
                'eventos': dia_data['eventos'],
                'horasCriticas': round(dia_data['horasCriticas'], 1)
            })
        
        resultado.sort(key=lambda x: x['periodo'])
        
        return {
            'tipo': 'diaria',
            'titulo': 'Tendencia Diaria',
            'datos': resultado
        }
        
    except Exception as e:
        logger.error(f"Error en tendencia diaria: {str(e)}")
        return {'tipo': 'diaria', 'titulo': 'Tendencia Diaria', 'datos': []}


def obtener_tendencia_semanal_real(client, fecha_inicio, fecha_fin, sucursal_filter):
    """Tendencia semana por semana"""
    try:
        # Usar la función común para calcular semanas
        return calcular_datos_semanales(client, fecha_inicio, fecha_fin, sucursal_filter, 'tendencia')
        
    except Exception as e:
        logger.error(f"Error en tendencia semanal: {str(e)}")
        return {'tipo': 'semanal', 'titulo': 'Tendencia Semanal', 'datos': []}


def obtener_tendencia_mensual(client, fecha_inicio, fecha_fin, sucursal_filter):
    """Tendencia mes por mes"""
    try:
        # Obtener eventos del período
        fecha_fin_completa = f"{fecha_fin}T23:59:59"
        eventos_query = client.table('eventos_temperatura')\
            .select('fecha_inicio, tipo, duracion_minutos')\
            .gte('fecha_inicio', fecha_inicio)\
            .lte('fecha_inicio', fecha_fin_completa)
        
        eventos_data = eventos_query.execute()
        
        # Agrupar por mes
        meses = {}
        if eventos_data.data:
            for evento in eventos_data.data:
                fecha_obj = datetime.fromisoformat(evento['fecha_inicio'])
                mes_key = fecha_obj.strftime('%Y-%m')
                mes_nombre = fecha_obj.strftime('%b %Y')
                
                if mes_key not in meses:
                    meses[mes_key] = {
                        'periodo': mes_nombre,
                        'eventos': 0,
                        'horasCriticas': 0
                    }
                
                meses[mes_key]['eventos'] += 1
                
                # Calcular horas críticas (deshielo + falla)
                duracion_min = evento.get('duracion_minutos', 0) or 0
                duracion_horas = duracion_min / 60.0
                
                tipo = evento['tipo']
                if tipo in ['DESHIELO_N', 'DESHIELO_P', 'FALLA', 'FALLA_EN_CURSO']:
                    meses[mes_key]['horasCriticas'] += duracion_horas
        
        # Convertir a lista ordenada
        resultado = []
        for mes_data in meses.values():
            resultado.append({
                'periodo': mes_data['periodo'],
                'eventos': mes_data['eventos'],
                'horasCriticas': round(mes_data['horasCriticas'], 1)
            })
        
        resultado.sort(key=lambda x: x['periodo'])
        
        return {
            'tipo': 'mensual',
            'titulo': 'Tendencia Mensual',
            'datos': resultado
        }
        
    except Exception as e:
        logger.error(f"Error en tendencia mensual: {str(e)}")
        return {'tipo': 'mensual', 'titulo': 'Tendencia Mensual', 'datos': []}


def calcular_datos_semanales(client, fecha_inicio, fecha_fin, sucursal_filter, tipo_calculo):
    """Función común para calcular datos semanales de manera consistente"""
    try:
        from datetime import timedelta
        
        # Obtener eventos del período (incluir todo el día final)
        fecha_fin_completa = f"{fecha_fin}T23:59:59"
        eventos_query = client.table('eventos_temperatura')\
            .select('tipo, duracion_minutos, fecha_inicio')\
            .gte('fecha_inicio', fecha_inicio)\
            .lte('fecha_inicio', fecha_fin_completa)
        
        eventos_data = eventos_query.execute()
        
        # Obtener lecturas solo si es para comparación
        lecturas_data = None
        if tipo_calculo == 'comparacion':
            lecturas_query = client.table('lecturas_temperatura')\
                .select('temperatura_c, timestamp')\
                .gte('timestamp', fecha_inicio)\
                .lte('timestamp', fecha_fin_completa)
            
            lecturas_data = lecturas_query.execute()
        
        # Inicializar semanas dentro del rango
        semanas = {}
        fecha_actual = datetime.fromisoformat(fecha_inicio)
        fecha_final = datetime.fromisoformat(fecha_fin)
        
        # Crear todas las semanas del período
        while fecha_actual <= fecha_final:
            # Obtener el lunes de la semana
            inicio_semana = fecha_actual - timedelta(days=fecha_actual.weekday())
            semana_key = inicio_semana.strftime('%Y-%m-%d')
            semana_nombre = f"Sem {inicio_semana.strftime('%d/%m')}"
            
            if semana_key not in semanas:
                semanas[semana_key] = {
                    'periodo': semana_nombre,
                    'eventos': 0,
                    'horasFalla': 0,
                    'horasCriticas': 0,
                    'tempPromedio': []
                }
            
            fecha_actual += timedelta(days=7)  # Avanzar una semana
        
        # Procesar eventos
        if eventos_data.data:
            for evento in eventos_data.data:
                fecha_obj = datetime.fromisoformat(evento['fecha_inicio'])
                # Obtener el lunes de la semana
                inicio_semana = fecha_obj - timedelta(days=fecha_obj.weekday())
                semana_key = inicio_semana.strftime('%Y-%m-%d')
                
                if semana_key in semanas:  # Solo si está en nuestro rango
                    semanas[semana_key]['eventos'] += 1
                    
                    duracion_min = evento.get('duracion_minutos', 0) or 0
                    duracion_horas = duracion_min / 60.0
                    tipo = evento['tipo']
                    
                    # Para comparación: solo horas de falla
                    if tipo in ['FALLA', 'FALLA_EN_CURSO']:
                        semanas[semana_key]['horasFalla'] += duracion_horas
                    
                    # Para tendencia: horas críticas (deshielo + falla)
                    if tipo in ['DESHIELO_N', 'DESHIELO_P', 'FALLA', 'FALLA_EN_CURSO']:
                        semanas[semana_key]['horasCriticas'] += duracion_horas
        
        # Procesar lecturas (solo para comparación)
        if lecturas_data and lecturas_data.data:
            for lectura in lecturas_data.data:
                fecha_obj = datetime.fromisoformat(lectura['timestamp'])
                inicio_semana = fecha_obj - timedelta(days=fecha_obj.weekday())
                semana_key = inicio_semana.strftime('%Y-%m-%d')
                
                if semana_key in semanas:
                    semanas[semana_key]['tempPromedio'].append(float(lectura['temperatura_c']))
        
        # Convertir a lista
        resultado = []
        for semana_data in semanas.values():
            if tipo_calculo == 'comparacion':
                temp_prom = sum(semana_data['tempPromedio']) / len(semana_data['tempPromedio']) if semana_data['tempPromedio'] else 0
                resultado.append({
                    'periodo': semana_data['periodo'],
                    'eventos': semana_data['eventos'],
                    'horasFalla': round(semana_data['horasFalla'], 1),
                    'tempPromedio': round(temp_prom, 1)
                })
            else:  # tendencia
                resultado.append({
                    'periodo': semana_data['periodo'],
                    'eventos': semana_data['eventos'],
                    'horasCriticas': round(semana_data['horasCriticas'], 1)
                })
        
        resultado.sort(key=lambda x: x['periodo'])
        
        # Para tendencia, si hay muy pocos datos, incluir períodos vacíos para mejor contexto
        if tipo_calculo == 'tendencia':
            datos_con_eventos = [r for r in resultado if r['eventos'] > 0]
            # Si hay muy pocos períodos con datos, mantener algunos vacíos para contexto
            if len(datos_con_eventos) <= 2 and len(resultado) > len(datos_con_eventos):
                # Mantener todos los datos para mostrar mejor contexto
                pass  # No filtrar
            else:
                # Filtrar solo si hay suficientes datos
                resultado = datos_con_eventos
        
        titulo = 'Comparación Semanal' if tipo_calculo == 'comparacion' else 'Tendencia Semanal'
        
        return {
            'tipo': 'semanal',
            'titulo': titulo,
            'datos': resultado
        }
        
    except Exception as e:
        logger.error(f"Error en cálculo semanal: {str(e)}")
        titulo = 'Comparación Semanal' if tipo_calculo == 'comparacion' else 'Tendencia Semanal'
        return {'tipo': 'semanal', 'titulo': titulo, 'datos': []}


def obtener_tendencia_semanal(client, fecha_inicio, fecha_fin, sucursal_filter):
    """Obtiene tendencia semanal de eventos usando datos reales"""
    try:
        # Obtener eventos del período
        eventos_query = client.table('eventos_temperatura')\
            .select('fecha_inicio, tipo, duracion_minutos')\
            .gte('fecha_inicio', fecha_inicio)\
            .lte('fecha_inicio', fecha_fin)
        
        eventos_data = eventos_query.execute()
        
        # Agrupar por semana
        semanas = {}
        if eventos_data.data:
            for evento in eventos_data.data:
                fecha_obj = datetime.fromisoformat(evento['fecha_inicio'])
                # Obtener el lunes de la semana
                inicio_semana = fecha_obj - timedelta(days=fecha_obj.weekday())
                semana_key = inicio_semana.strftime('%Y-%m-%d')
                semana_nombre = f"Semana {inicio_semana.strftime('%d/%m')}"
                
                if semana_key not in semanas:
                    semanas[semana_key] = {
                        'semana': semana_nombre,
                        'eventos': 0,
                        'horasCriticas': 0
                    }
                
                semanas[semana_key]['eventos'] += 1
                
                # Calcular horas críticas (deshielo + falla)
                duracion_min = evento.get('duracion_minutos', 0) or 0
                duracion_horas = duracion_min / 60.0
                
                tipo = evento['tipo']
                if tipo in ['DESHIELO_N', 'DESHIELO_P', 'FALLA', 'FALLA_EN_CURSO']:
                    semanas[semana_key]['horasCriticas'] += duracion_horas
        
        # Convertir a lista ordenada
        resultado = []
        for semana_data in semanas.values():
            resultado.append({
                'semana': semana_data['semana'],
                'eventos': semana_data['eventos'],
                'horasCriticas': round(semana_data['horasCriticas'], 1)
            })
        
        resultado.sort(key=lambda x: x['semana'])
        return resultado
        
    except Exception as e:
        logger.error(f"Error en tendencia semanal: {str(e)}")
        return []


def obtener_analisis_eventos(client, fecha_inicio, fecha_fin, sucursal_filter):
    """Obtiene análisis detallado de eventos usando datos reales - distribución por TIEMPO, no por cantidad"""
    try:
        # Obtener eventos del período (incluir todo el día final)
        fecha_fin_completa = f"{fecha_fin}T23:59:59"
        eventos_query = client.table('eventos_temperatura')\
            .select('*')\
            .gte('fecha_inicio', fecha_inicio)\
            .lte('fecha_inicio', fecha_fin_completa)
        
        eventos_data = eventos_query.execute()
        
        # Calcular tiempo total del período en minutos
        fecha_inicio_obj = datetime.fromisoformat(fecha_inicio)
        fecha_fin_obj = datetime.fromisoformat(fecha_fin)
        dias_periodo = (fecha_fin_obj - fecha_inicio_obj).days + 1
        minutos_totales = dias_periodo * 24 * 60  # Total de minutos en el período
        
        # Contar tiempo por tipo (en minutos)
        tiempo_deshielo = 0
        tiempo_falla = 0
        eventos_criticos = []
        
        if eventos_data.data:
            for evento in eventos_data.data:
                tipo = evento['tipo']
                duracion_min = evento.get('duracion_minutos', 0) or 0
                
                if tipo in ['DESHIELO_N', 'DESHIELO_P']:
                    tiempo_deshielo += duracion_min
                elif tipo in ['FALLA', 'FALLA_EN_CURSO']:
                    tiempo_falla += duracion_min
                
                # Eventos críticos (duración > 2 horas o temp > 6°C)
                temp_max = float(evento.get('temp_max_c', 0) or 0)
                
                if duracion_min > 120 or temp_max > 6:
                    eventos_criticos.append({
                        'id': evento['id'],
                        'camara': f"Cámara {evento['camara_id']}",
                        'tipo': tipo,
                        'duracion': f"{duracion_min // 60}h {duracion_min % 60}m" if duracion_min > 0 else "N/A",
                        'tempMaxima': temp_max,
                        'estado': evento.get('estado', 'DESCONOCIDO')
                    })
        
        # Calcular tiempo normal (tiempo total - tiempo en eventos)
        tiempo_eventos = tiempo_deshielo + tiempo_falla
        tiempo_normal = minutos_totales - tiempo_eventos
        
        # Asegurar que no haya valores negativos
        if tiempo_normal < 0:
            tiempo_normal = 0
        
        # Calcular distribución porcentual por TIEMPO
        distribucion = []
        if minutos_totales > 0:
            porcentaje_normal = round((tiempo_normal / minutos_totales) * 100, 1)
            porcentaje_deshielo = round((tiempo_deshielo / minutos_totales) * 100, 1)
            porcentaje_falla = round((tiempo_falla / minutos_totales) * 100, 1)
            
            # Solo incluir estados que tienen tiempo > 0
            if porcentaje_normal > 0:
                distribucion.append({
                    'estado': 'NORMAL',
                    'valor': round(tiempo_normal / 60, 1),  # Convertir a horas para mostrar
                    'porcentaje': porcentaje_normal
                })
            
            if porcentaje_deshielo > 0:
                distribucion.append({
                    'estado': 'DESHIELO',
                    'valor': round(tiempo_deshielo / 60, 1),  # Convertir a horas para mostrar
                    'porcentaje': porcentaje_deshielo
                })
            
            if porcentaje_falla > 0:
                distribucion.append({
                    'estado': 'FALLA',
                    'valor': round(tiempo_falla / 60, 1),  # Convertir a horas para mostrar
                    'porcentaje': porcentaje_falla
                })
        
        return {
            'distribucion': distribucion,
            'eventosCriticos': eventos_criticos[:10]  # Top 10
        }
        
    except Exception as e:
        logger.error(f"Error en análisis de eventos: {str(e)}")
        return {
            'distribucion': [],
            'eventosCriticos': []
        }


def obtener_temperaturas_diarias(client, fecha_inicio, fecha_fin, sucursal_filter):
    """Obtiene evolución de temperaturas diarias usando datos reales"""
    try:
        # Obtener lecturas del período
        lecturas_query = client.table('lecturas_temperatura')\
            .select('temperatura_c, timestamp')\
            .gte('timestamp', fecha_inicio)\
            .lte('timestamp', fecha_fin)
        
        lecturas_data = lecturas_query.execute()
        
        # Agrupar por fecha
        fechas = {}
        if lecturas_data.data:
            for lectura in lecturas_data.data:
                fecha_str = lectura['timestamp'][:10]  # YYYY-MM-DD
                temp = float(lectura['temperatura_c'])
                
                if fecha_str not in fechas:
                    fechas[fecha_str] = {
                        'fecha': fecha_str,
                        'temperaturas': []
                    }
                
                fechas[fecha_str]['temperaturas'].append(temp)
        
        # Calcular promedios y máximos por día
        resultado = []
        for fecha_data in fechas.values():
            temps = fecha_data['temperaturas']
            if temps:
                temp_prom = sum(temps) / len(temps)
                temp_max = max(temps)
                
                resultado.append({
                    'fecha': fecha_data['fecha'],
                    'tempPromedio': round(temp_prom, 1),
                    'tempMaxima': round(temp_max, 1),
                    'umbralCritico': 4.0  # Línea de referencia
                })
        
        resultado.sort(key=lambda x: x['fecha'])
        return resultado
        
    except Exception as e:
        logger.error(f"Error en temperaturas diarias: {str(e)}")
        return []


def obtener_ranking_camaras(client, fecha_inicio, fecha_fin, sucursal_filter):
    """Obtiene ranking de cámaras por eventos y fallas usando datos reales"""
    try:
        # Obtener eventos del período
        eventos_query = client.table('eventos_temperatura')\
            .select('camara_id, tipo, duracion_minutos')\
            .gte('fecha_inicio', fecha_inicio)\
            .lte('fecha_inicio', fecha_fin)
        
        eventos_data = eventos_query.execute()
        
        # Agrupar por cámara
        camaras = {}
        if eventos_data.data:
            for evento in eventos_data.data:
                camara_id = evento['camara_id']
                
                if camara_id not in camaras:
                    camaras[camara_id] = {
                        'id': camara_id,
                        'nombre': f'Cámara {camara_id}',
                        'eventos': 0,
                        'horasFalla': 0
                    }
                
                camaras[camara_id]['eventos'] += 1
                
                # Calcular horas de falla
                if evento['tipo'] in ['FALLA', 'FALLA_EN_CURSO']:
                    duracion_min = evento.get('duracion_minutos', 0) or 0
                    camaras[camara_id]['horasFalla'] += duracion_min / 60.0
        
        # Convertir a listas y ordenar
        lista_camaras = list(camaras.values())
        
        mas_eventos = sorted(lista_camaras, key=lambda x: x['eventos'], reverse=True)[:5]
        mas_fallas = sorted(lista_camaras, key=lambda x: x['horasFalla'], reverse=True)[:5]
        
        # Redondear horas de falla
        for camara in mas_fallas:
            camara['horasFalla'] = round(camara['horasFalla'], 1)
        
        return {
            'masEventos': mas_eventos,
            'masFallas': mas_fallas
        }
        
    except Exception as e:
        logger.error(f"Error en ranking de cámaras: {str(e)}")
        return {
            'masEventos': [],
            'masFallas': []
        }


@api_view(['POST'])
@permission_classes([AllowAny])
def guardar_resumen_ejecutivo(request):
    """
    Guarda un resumen ejecutivo en la base de datos.
    
    POST /api/dashboard/guardar-resumen-ejecutivo/
    
    Body:
        {
            "fechaInicio": "2025-09-01",
            "fechaFin": "2025-09-30",
            "titulo": "Resumen Septiembre 2025",
            "observaciones": "Análisis mensual de operación",
            "datos": { ... } // Datos completos del análisis
        }
    """
    try:
        user = getattr(request, 'firebase_user', None)
        client = get_supabase_client(use_service_key=True)
        
        # Obtener datos del request
        data = request.data
        fecha_inicio = data.get('fechaInicio')
        fecha_fin = data.get('fechaFin')
        titulo = data.get('titulo', f'Resumen {fecha_inicio} a {fecha_fin}')
        observaciones = data.get('observaciones', '')
        datos_analisis = data.get('datos', {})
        usuario_info = data.get('usuarioInfo', {})  # Información del usuario del frontend
        
        # Usar información del usuario (priorizar middleware, luego frontend)
        usuario_final = user if user else usuario_info
        
        logger.info(f"Guardando resumen ejecutivo para período {fecha_inicio} a {fecha_fin}")
        if usuario_final:
            logger.info(f"Usuario: {usuario_final.get('email', 'N/A')}")
        else:
            logger.warning("No hay información de usuario disponible")
        
        if not fecha_inicio or not fecha_fin:
            return Response({
                'error': 'fechaInicio y fechaFin son requeridos'
            }, status=400)
        
        # Preparar datos para insertar (sin sucursal_id ni camara_id)
        resumen_data = {
            'fecha_inicio': fecha_inicio,
            'fecha_fin': fecha_fin,
            'titulo': titulo,
            'observaciones': observaciones,
            'kpis': datos_analisis.get('kpis', {}),
            'comparacion_adaptativa': datos_analisis.get('comparacionAdaptativa', {}),
            'tendencia_adaptativa': datos_analisis.get('tendenciaAdaptativa', {}),
            'analisis_eventos': datos_analisis.get('analisisEventos', {}),
            'temperaturas_diarias': datos_analisis.get('temperaturas', []),
            'ranking_camaras': datos_analisis.get('rankingCamaras', {})
        }
        
        # Información del usuario (solo email y nombre)
        if usuario_final:
            resumen_data['usuario_email'] = usuario_final.get('email', 'usuario@sistema.com')
            resumen_data['usuario_nombre'] = usuario_final.get('nombre', usuario_final.get('displayName', 'Usuario'))
            logger.info(f"Usuario: {usuario_final.get('email', 'N/A')}")
        else:
            resumen_data['usuario_email'] = 'anonimo@sistema.com'
            resumen_data['usuario_nombre'] = 'Usuario Anónimo'
            logger.warning("No hay información de usuario disponible")
        
        # Insertar en la base de datos
        result = client.table('resumenes_ejecutivos').insert(resumen_data).execute()
        
        if result.data:
            return Response({
                'success': True,
                'id': result.data[0]['id'],
                'message': 'Resumen guardado exitosamente'
            })
        else:
            return Response({
                'error': 'Error al guardar el resumen'
            }, status=500)
        
    except Exception as e:
        logger.error(f"Error al guardar resumen ejecutivo: {str(e)}")
        return Response({
            'error': f'Error interno: {str(e)}'
        }, status=500)



@api_view(['GET'])
@permission_classes([AllowAny])
def get_resumenes_ejecutivos(request):
    """
    Obtiene la lista de resúmenes ejecutivos guardados.
    
    GET /api/dashboard/resumenes-ejecutivos/
    
    Query params:
        - limit: Número máximo de resultados (default: 20)
        - offset: Desplazamiento para paginación
    """
    try:
        user = getattr(request, 'firebase_user', None)
        client = get_supabase_client(use_service_key=True)
        
        # Parámetros de paginación
        limit = int(request.GET.get('limit', 20))
        offset = int(request.GET.get('offset', 0))
        
        # Construir query
        query = client.table('resumenes_ejecutivos')\
            .select('id, created_at, fecha_inicio, fecha_fin, titulo, usuario_nombre, observaciones')\
            .order('created_at', desc=True)\
            .range(offset, offset + limit - 1)
        
        # Filtrar por sucursal si no es admin
        if user and user.get('rol') != 'ADMIN':
            sucursal_id = user.get('sucursal_id')
            if sucursal_id:
                query = query.eq('sucursal_id', sucursal_id)
        
        result = query.execute()
        
        return Response({
            'resumenes': result.data or [],
            'total': len(result.data) if result.data else 0
        })
        
    except Exception as e:
        logger.error(f"Error al obtener resúmenes ejecutivos: {str(e)}")
        return Response({
            'resumenes': [],
            'total': 0
        })


@api_view(['GET'])
@permission_classes([AllowAny])
def get_resumen_semanal(request):
    """
    Obtiene resumen de temperaturas de la última semana desde lecturas.
    
    GET /api/dashboard/resumen-semanal/
    
    Returns:
        Estadísticas agregadas de la semana
    """
    try:
        user = request.firebase_user
        client = get_supabase_client(use_service_key=True)
        
        # Últimos 7 días
        hace_7_dias = date.today() - timedelta(days=7)
        
        # Obtener lecturas de la última semana
        lecturas_query = client.table('lecturas_temperatura')\
            .select('timestamp, temperatura_c, camara_id')\
            .gte('timestamp', hace_7_dias.isoformat())
        
        # Filtrar por sucursal si no es ADMIN
        if user and user.get('rol') != 'ADMIN':
            sucursal_id = user.get('sucursal_id')
            if sucursal_id:
                lecturas_query = client.table('lecturas_temperatura')\
                    .select('timestamp, temperatura_c, camara_id, camaras_frio!inner(sucursal_id)')\
                    .gte('timestamp', hace_7_dias.isoformat())\
                    .eq('camaras_frio.sucursal_id', sucursal_id)
        
        lecturas_response = lecturas_query.execute()
        
        # Agrupar por fecha
        por_fecha = {}
        if lecturas_response.data:
            for lectura in lecturas_response.data:
                fecha_str = lectura['timestamp'][:10]  # YYYY-MM-DD
                temp = float(lectura['temperatura_c'])
                
                if fecha_str not in por_fecha:
                    por_fecha[fecha_str] = {
                        'fecha': fecha_str,
                        'temp_min': temp,
                        'temp_max': temp,
                        'temps': [temp],
                        'alertas': 0,
                        'fallas': 0,
                    }
                else:
                    por_fecha[fecha_str]['temp_min'] = min(por_fecha[fecha_str]['temp_min'], temp)
                    por_fecha[fecha_str]['temp_max'] = max(por_fecha[fecha_str]['temp_max'], temp)
                    por_fecha[fecha_str]['temps'].append(temp)
        
        # Calcular promedios y obtener eventos
        resultado = []
        for fecha_str, data in por_fecha.items():
            # Calcular promedio
            temp_promedio = sum(data['temps']) / len(data['temps'])
            
            # Contar eventos del día
            eventos_query = client.table('eventos_temperatura')\
                .select('tipo')\
                .gte('fecha_inicio', f'{fecha_str}T00:00:00')\
                .lt('fecha_inicio', f'{fecha_str}T23:59:59')
            
            if user and user.get('rol') != 'ADMIN':
                sucursal_id = user.get('sucursal_id')
                if sucursal_id:
                    eventos_query = client.table('eventos_temperatura')\
                        .select('tipo, camaras_frio!inner(sucursal_id)')\
                        .gte('fecha_inicio', f'{fecha_str}T00:00:00')\
                        .lt('fecha_inicio', f'{fecha_str}T23:59:59')\
                        .eq('camaras_frio.sucursal_id', sucursal_id)
            
            eventos_response = eventos_query.execute()
            
            alertas = 0
            fallas = 0
            if eventos_response.data:
                for evento in eventos_response.data:
                    tipo = evento['tipo']
                    if tipo in ['DESHIELO_N', 'DESHIELO_P']:
                        alertas += 1
                    elif tipo in ['FALLA', 'FALLA_EN_CURSO']:
                        fallas += 1
            
            resultado.append({
                'fecha': fecha_str,
                'temp_min': round(data['temp_min'], 2),
                'temp_max': round(data['temp_max'], 2),
                'temp_promedio': round(temp_promedio, 2),
                'alertas': alertas,
                'fallas': fallas,
            })
        
        # Ordenar por fecha
        resultado.sort(key=lambda x: x['fecha'])
        
        return Response(resultado)
        
    except Exception as e:
        logger.error(f"Error al obtener resumen semanal: {str(e)}")
        return Response([])
