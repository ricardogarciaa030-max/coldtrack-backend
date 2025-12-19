# 🔧 ColdTrack Backend

Sistema de monitoreo de temperatura para cámaras de frío con sincronización Firebase ↔ Supabase.

## 🚀 Inicio Rápido

### 1. Activar entorno virtual e instalar dependencias
```bash
cd backend
venv\Scripts\python.exe -m pip install -r requirements.txt
```

### 2. Configurar variables de entorno
Editar `backend/.env` con tus credenciales:
```env
# Firebase
FIREBASE_CREDENTIALS_PATH=firebase-credentials.json
FIREBASE_PROJECT_ID=tu-proyecto-firebase

# Supabase
SUPABASE_URL=https://tu-proyecto.supabase.co
SUPABASE_SERVICE_KEY=tu-service-key
SUPABASE_ANON_KEY=tu-anon-key
```

### 3. Iniciar servidor Django
```bash
venv\Scripts\python.exe manage.py runserver 0.0.0.0:8000
```

### 4. Iniciar sincronización automática (opcional)
```bash
venv\Scripts\python.exe sync_live_events.py monitor
```

## 📡 Endpoints Principales

### Dashboard
- `GET /api/dashboard/kpis/` - KPIs del dashboard
- `GET /api/dashboard/eventos-recientes/` - Últimos eventos
- `GET /api/dashboard/eventos-por-dia/` - Eventos por día (7 días)

### Eventos
- `GET /api/eventos/?fecha_desde=YYYY-MM-DD&fecha_hasta=YYYY-MM-DD` - Búsqueda histórica

### Usuarios
- `GET /api/users/` - Lista de usuarios

### Cámaras y Sucursales
- `GET /api/camaras/` - Lista de cámaras
- `GET /api/sucursales/` - Lista de sucursales

## 🔄 Sincronización

### Scripts Disponibles
- `sync_live_events.py` - Monitor de eventos en tiempo real
- `sync_historical_data.py` - Migración de datos históricos
- `sync_all_events_today.py` - Sincronizar eventos del día actual

### Uso del Monitor
```bash
# Ejecutar una vez
venv\Scripts\python.exe sync_live_events.py

# Monitor continuo (cada 30 segundos)
venv\Scripts\python.exe sync_live_events.py monitor
```

## 🏗️ Arquitectura

### Servicios Principales
- `services/firebase_service.py` - Conexión y consultas a Firebase
- `services/supabase_service.py` - Conexión y operaciones en Supabase

### Apps Django
- `apps/auth/` - Autenticación con Firebase
- `apps/dashboard/` - KPIs y estadísticas
- `apps/eventos/` - Gestión de eventos de temperatura
- `apps/camaras/` - Gestión de cámaras
- `apps/usuarios/` - Gestión de usuarios

## 🔧 Configuración

### Base de Datos
El sistema usa **Supabase** como base de datos principal. Firebase se usa solo como fuente de datos en tiempo real.

### Autenticación
- Firebase Auth para autenticación de usuarios
- Middleware personalizado para validación de tokens
- Permisos basados en roles (ADMIN, ENCARGADO, SUBJEFE)

### Variables de Entorno Importantes
```env
DEBUG=True                    # Solo para desarrollo
SECRET_KEY=tu-secret-key     # Cambiar en producción
CORS_ALLOWED_ORIGINS=http://localhost:5173
```

## 🛠️ Comandos Útiles

### Verificar configuración
```bash
venv\Scripts\python.exe manage.py check
```

### Verificar conexión a Supabase
```bash
venv\Scripts\python.exe -c "from services.supabase_service import get_supabase_client; print('✅ Supabase OK')"
```

### Verificar conexión a Firebase
```bash
venv\Scripts\python.exe -c "from services.firebase_service import initialize_firebase; initialize_firebase(); print('✅ Firebase OK')"
```

## 📝 Notas Importantes

- **Siempre usar** `venv\Scripts\python.exe` para ejecutar comandos
- **RLS debe estar deshabilitado** en Supabase para funcionamiento correcto
- **Firebase credentials** deben estar en `firebase-credentials.json`
- **Puerto 8000** debe estar libre para el servidor Django

## 🔒 Seguridad

- Tokens JWT validados con Firebase Admin SDK
- Service key de Supabase para operaciones administrativas
- CORS configurado para frontend específico
- Middleware de autenticación personalizado