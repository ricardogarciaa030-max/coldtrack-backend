# Arquitectura de ColdTrack Backend

## Visión General

El backend de ColdTrack está construido con Django y Django REST Framework, siguiendo principios de Clean Code y arquitectura modular.

## Estructura de Módulos

```
backend/
├── coldtrack/              # Configuración principal del proyecto
│   ├── settings.py        # Configuración de Django
│   ├── urls.py            # Rutas principales
│   └── wsgi.py            # Punto de entrada WSGI
├── services/              # Servicios compartidos
│   ├── firebase_service.py    # Interacción con Firebase
│   └── supabase_service.py    # Interacción con Supabase
└── apps/                  # Módulos de la aplicación
    ├── auth/              # Autenticación Firebase
    ├── users/             # Gestión de usuarios
    ├── sucursales/        # Gestión de sucursales
    ├── camaras/           # Gestión de cámaras
    ├── lecturas/          # Lecturas de temperatura
    ├── eventos/           # Eventos de temperatura
    ├── dashboard/         # KPIs y estadísticas
    └── sync/              # Sincronización Firebase → Supabase
```

## Principios de Diseño

### 1. Separación de Responsabilidades

Cada módulo tiene una responsabilidad única y bien definida:

- **models.py**: Solo definición de modelos (mapeo de tablas)
- **serializers.py**: Solo validación y serialización de datos
- **views.py**: Solo endpoints y lógica de presentación
- **services.py**: Solo lógica de negocio
- **urls.py**: Solo definición de rutas

### 2. Servicios Compartidos

Los servicios de Firebase y Supabase están centralizados en `services/`:

- **firebase_service.py**: Todas las operaciones de lectura de Firebase
- **supabase_service.py**: Todas las operaciones de escritura en Supabase

Esto evita duplicación de código y facilita el mantenimiento.

### 3. Modelos No Gestionados

Los modelos de Django tienen `managed = False` porque las tablas ya existen en Supabase:

```python
class Meta:
    db_table = 'sucursales'
    managed = False  # Django no gestiona esta tabla
```

Esto permite usar el ORM de Django sin que Django intente crear/modificar las tablas.

### 4. Autenticación con Middleware

El middleware `FirebaseAuthMiddleware` intercepta todas las requests y:

1. Extrae el token del header `Authorization`
2. Valida el token con Firebase Admin SDK
3. Busca el usuario en Supabase
4. Agrega `request.firebase_user` con los datos del usuario

### 5. Permisos Basados en Roles

Los permisos se definen en `apps/auth/permissions.py`:

- **IsAdmin**: Solo usuarios con rol ADMIN
- **IsAdminOrReadOnly**: ADMIN puede editar, otros solo leer
- **CanAccessSucursal**: Filtra por sucursal según el rol
- **CanEditSucursal**: Permite editar según rol y sucursal

### 6. Filtrado Automático por Sucursal

La función `filter_by_sucursal()` aplica filtros automáticamente:

```python
def get_queryset(self):
    queryset = super().get_queryset()
    if hasattr(self.request, 'firebase_user'):
        queryset = filter_by_sucursal(queryset, self.request.firebase_user)
    return queryset
```

- **ADMIN**: Ve todos los registros
- **ENCARGADO/SUBJEFE**: Solo ve registros de su sucursal

## Flujo de Datos

### Lectura de Datos en Tiempo Real

```
Frontend → Firebase Realtime DB (lectura directa)
```

El frontend lee directamente desde Firebase para obtener datos en tiempo real sin pasar por el backend.

### Consulta de Datos Históricos

```
Frontend → Backend Django → Supabase PostgreSQL → Frontend
```

El frontend consulta el backend, que a su vez consulta Supabase y retorna los datos.

### Sincronización de Datos

```
Firebase Realtime DB → Backend Django (sync) → Supabase PostgreSQL
```

El comando `sync_firebase` lee datos de Firebase y los escribe en Supabase:

1. Lee lecturas de temperatura desde `/status` y `/controles`
2. Lee eventos desde `/eventos`
3. Inserta lecturas en `lecturas_temperatura`
4. Inserta/actualiza eventos en `eventos_temperatura`
5. Genera resúmenes diarios en `resumen_diario_camara`

## Módulos Detallados

### apps/auth

**Propósito**: Autenticación con Firebase

**Componentes**:
- `middleware.py`: Valida tokens en cada request
- `permissions.py`: Define permisos basados en roles
- `views.py`: Endpoints de autenticación

**Endpoints**:
- `POST /api/auth/verify-token/`: Valida token y retorna usuario
- `GET /api/auth/me/`: Obtiene usuario actual

### apps/users

**Propósito**: Gestión de usuarios del sistema

**Modelo**: `Usuario` (mapea tabla `usuarios`)

**Endpoints**:
- `GET /api/users/`: Lista usuarios (solo ADMIN)
- `POST /api/users/`: Crea usuario (solo ADMIN)
- `PUT /api/users/{id}/`: Actualiza usuario (solo ADMIN)
- `DELETE /api/users/{id}/`: Elimina usuario (solo ADMIN)

### apps/sucursales

**Propósito**: Gestión de sucursales

**Modelo**: `Sucursal` (mapea tabla `sucursales`)

**Endpoints**:
- `GET /api/sucursales/`: Lista sucursales
- `GET /api/sucursales/activas/`: Lista solo sucursales activas
- `POST /api/sucursales/`: Crea sucursal (solo ADMIN)
- `PUT /api/sucursales/{id}/`: Actualiza sucursal (solo ADMIN)
- `DELETE /api/sucursales/{id}/`: Elimina sucursal (solo ADMIN)

### apps/camaras

**Propósito**: Gestión de cámaras de frío

**Modelo**: `CamaraFrio` (mapea tabla `camaras_frio`)

**Endpoints**:
- `GET /api/camaras/`: Lista cámaras
- `GET /api/camaras/{id}/live_status/`: Obtiene estado en vivo desde Firebase
- `POST /api/camaras/`: Crea cámara (solo ADMIN)
- `PUT /api/camaras/{id}/`: Actualiza cámara (solo ADMIN)
- `DELETE /api/camaras/{id}/`: Elimina cámara (solo ADMIN)

### apps/lecturas

**Propósito**: Consulta de lecturas históricas

**Modelos**:
- `LecturaTemperatura` (mapea tabla `lecturas_temperatura`)
- `ResumenDiarioCamara` (mapea tabla `resumen_diario_camara`)

**Endpoints**:
- `GET /api/lecturas/temperaturas/`: Lista lecturas (con filtros)
- `GET /api/lecturas/resumen-diario/`: Lista resúmenes diarios (con filtros)

### apps/eventos

**Propósito**: Gestión de eventos de temperatura

**Modelo**: `EventoTemperatura` (mapea tabla `eventos_temperatura`)

**Endpoints**:
- `GET /api/eventos/`: Lista eventos (con filtros)
- `GET /api/eventos/recientes/`: Eventos de las últimas 24h
- `GET /api/eventos/en_curso/`: Eventos actualmente en curso
- `PATCH /api/eventos/{id}/`: Actualiza evento (ENCARGADO puede agregar observaciones)

### apps/dashboard

**Propósito**: KPIs y estadísticas para el dashboard

**Endpoints**:
- `GET /api/dashboard/kpis/`: KPIs principales
- `GET /api/dashboard/eventos-por-dia/`: Eventos agrupados por día
- `GET /api/dashboard/eventos-recientes/`: Últimos 10 eventos
- `GET /api/dashboard/resumen-semanal/`: Resumen de la última semana

### apps/sync

**Propósito**: Sincronización Firebase → Supabase

**Componentes**:
- `services.py`: Lógica de sincronización
- `management/commands/sync_firebase.py`: Comando de Django

**Funciones**:
- `sync_device_readings()`: Sincroniza lecturas de un dispositivo
- `sync_device_events()`: Sincroniza eventos de un dispositivo
- `generate_daily_summary()`: Genera resumen diario
- `sync_all_devices()`: Sincroniza todos los dispositivos

**Uso**:
```bash
python manage.py sync_firebase
python manage.py sync_firebase --device-id DEVICE_001
python manage.py sync_firebase --date 2025-12-08
```

## Servicios Compartidos

### services/firebase_service.py

**Funciones**:
- `initialize_firebase()`: Inicializa Firebase Admin SDK
- `get_live_status(device_id)`: Obtiene estado en vivo
- `get_daily_controls(device_id, date)`: Obtiene controles del día
- `get_firebase_events(device_id, date)`: Obtiene eventos del día
- `get_all_devices()`: Lista todos los dispositivos

### services/supabase_service.py

**Funciones**:
- `get_supabase_client()`: Obtiene cliente de Supabase
- `get_camera_by_firebase_path(path)`: Busca cámara por device_id
- `insert_temperature_reading()`: Inserta lectura
- `insert_event()`: Inserta evento
- `update_event_end()`: Actualiza fin de evento
- `insert_daily_summary()`: Inserta/actualiza resumen diario
- `get_open_events_for_camera()`: Obtiene eventos abiertos

## Configuración

### settings.py

**Configuraciones importantes**:

- `INSTALLED_APPS`: Incluye todos los módulos de ColdTrack
- `MIDDLEWARE`: Incluye `FirebaseAuthMiddleware`
- `REST_FRAMEWORK`: Configuración de DRF
- `CORS_ALLOWED_ORIGINS`: Orígenes permitidos para CORS
- `FIREBASE_CONFIG`: Credenciales de Firebase Admin SDK
- `SUPABASE_CONFIG`: Credenciales de Supabase

### Variables de Entorno

Ver `.env.example` para la lista completa de variables requeridas.

## Testing

Para ejecutar tests:

```bash
python manage.py test
```

## Logging

El sistema usa logging de Python para registrar eventos:

- **INFO**: Operaciones normales
- **WARNING**: Situaciones inusuales pero manejables
- **ERROR**: Errores que requieren atención

Los logs se muestran en la consola durante el desarrollo.

## Seguridad

### Autenticación

- Todos los endpoints requieren autenticación (excepto `/api/auth/verify-token/`)
- Los tokens de Firebase se validan en cada request
- Los tokens expirados son rechazados automáticamente

### Autorización

- Los permisos se verifican en cada endpoint
- Los usuarios solo pueden acceder a datos de su sucursal (excepto ADMIN)
- Las operaciones de escritura están restringidas según el rol

### CORS

- Solo los orígenes configurados en `CORS_ALLOWED_ORIGINS` pueden acceder a la API
- En producción, configurar solo los dominios necesarios

## Performance

### Optimizaciones

- Uso de `select_related()` para reducir queries a la base de datos
- Paginación automática en listados (50 items por página)
- Índices en las tablas de Supabase para consultas rápidas

### Caching

Actualmente no se usa caching, pero se puede agregar:

- Redis para cachear KPIs
- Cache de Django para resultados de queries frecuentes

## Escalabilidad

### Horizontal

- El backend es stateless, se puede escalar horizontalmente
- Usar un load balancer para distribuir requests

### Vertical

- Aumentar recursos del servidor según la carga
- Optimizar queries si hay problemas de performance

### Base de Datos

- Supabase maneja el escalado de PostgreSQL
- Agregar índices según patrones de consulta

## Mantenimiento

### Agregar un Nuevo Módulo

1. Crear carpeta en `apps/nuevo_modulo/`
2. Crear archivos: `__init__.py`, `apps.py`, `models.py`, `serializers.py`, `views.py`, `urls.py`
3. Registrar en `INSTALLED_APPS` en `settings.py`
4. Incluir URLs en `coldtrack/urls.py`

### Agregar un Nuevo Endpoint

1. Definir función/método en `views.py`
2. Agregar ruta en `urls.py`
3. Aplicar permisos necesarios
4. Documentar en este archivo

### Modificar Permisos

1. Editar `apps/auth/permissions.py`
2. Aplicar el nuevo permiso en las vistas correspondientes
3. Probar con diferentes roles

## Troubleshooting

### Error: "Firebase credentials not configured"

- Verificar variables de entorno de Firebase
- Verificar que `FIREBASE_PRIVATE_KEY` tenga formato correcto

### Error: "Connection to database failed"

- Verificar `DATABASE_URL`
- Verificar que Supabase esté accesible

### Error: "User not found in system"

- Verificar que el usuario exista en tabla `usuarios`
- Verificar que `firebase_uid` coincida con Firebase Auth

### Queries Lentas

- Revisar logs de queries con `DEBUG=True`
- Agregar índices en Supabase
- Usar `select_related()` y `prefetch_related()`
