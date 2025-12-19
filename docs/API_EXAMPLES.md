# Ejemplos de Uso de la API - ColdTrack

## Autenticación

Todos los endpoints (excepto `/api/auth/verify-token/`) requieren un token de Firebase en el header:

```
Authorization: Bearer <firebase_id_token>
```

### Obtener Token

Desde el frontend, después del login con Firebase:

```javascript
const user = auth.currentUser;
const token = await user.getIdToken();
```

## Endpoints

### 1. Verificar Token

**POST** `/api/auth/verify-token/`

Request:
```json
{
  "token": "eyJhbGciOiJSUzI1NiIsImtpZCI6..."
}
```

Response:
```json
{
  "user": {
    "uid": "abc123",
    "id": 1,
    "email": "admin@example.com",
    "nombre": "Juan Pérez",
    "rol": "ADMIN",
    "sucursal_id": null
  }
}
```

### 2. Obtener Usuario Actual

**GET** `/api/auth/me/`

Headers:
```
Authorization: Bearer <token>
```

Response:
```json
{
  "user": {
    "uid": "abc123",
    "id": 1,
    "email": "admin@example.com",
    "nombre": "Juan Pérez",
    "rol": "ADMIN",
    "sucursal_id": null
  }
}
```

### 3. Obtener KPIs del Dashboard

**GET** `/api/dashboard/kpis/`

Response:
```json
{
  "camaras_activas": 15,
  "sucursales_activas": 3,
  "eventos_hoy": 5,
  "camaras_con_eventos_24h": 3
}
```

### 4. Obtener Eventos por Día

**GET** `/api/dashboard/eventos-por-dia/`

Response:
```json
[
  {
    "fecha": "2025-12-01",
    "total": 5
  },
  {
    "fecha": "2025-12-02",
    "total": 3
  }
]
```

### 5. Obtener Eventos Recientes

**GET** `/api/dashboard/eventos-recientes/`

Response:
```json
[
  {
    "id": 123,
    "tipo": "DESHIELO_N",
    "estado": "RESUELTO",
    "fecha_inicio": "2025-12-08T10:30:00Z",
    "fecha_fin": "2025-12-08T11:00:00Z",
    "temp_max_c": 8.5,
    "camara": {
      "id": 1,
      "nombre": "Cámara 1"
    },
    "sucursal": {
      "id": 1,
      "nombre": "Sucursal Centro"
    }
  }
]
```

### 6. Listar Sucursales

**GET** `/api/sucursales/`

Response:
```json
{
  "count": 3,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "created_at": "2025-01-01T00:00:00Z",
      "nombre": "Sucursal Centro",
      "direccion": "Av. Principal 123",
      "descripcion": "Sucursal principal",
      "activa": true
    }
  ]
}
```

### 7. Crear Sucursal (Solo ADMIN)

**POST** `/api/sucursales/`

Request:
```json
{
  "nombre": "Sucursal Norte",
  "direccion": "Calle Norte 456",
  "descripcion": "Sucursal zona norte",
  "activa": true
}
```

Response:
```json
{
  "id": 2,
  "created_at": "2025-12-08T12:00:00Z",
  "nombre": "Sucursal Norte",
  "direccion": "Calle Norte 456",
  "descripcion": "Sucursal zona norte",
  "activa": true
}
```

### 8. Actualizar Sucursal (Solo ADMIN)

**PUT** `/api/sucursales/2/`

Request:
```json
{
  "nombre": "Sucursal Norte Actualizada",
  "direccion": "Calle Norte 456",
  "descripcion": "Sucursal zona norte",
  "activa": true
}
```

### 9. Listar Cámaras

**GET** `/api/camaras/`

Query params opcionales:
- `sucursal_id`: Filtrar por sucursal

Response:
```json
{
  "count": 5,
  "results": [
    {
      "id": 1,
      "created_at": "2025-01-01T00:00:00Z",
      "sucursal": 1,
      "sucursal_data": {
        "id": 1,
        "nombre": "Sucursal Centro"
      },
      "nombre": "Cámara 1",
      "codigo": "CAM-001",
      "firebase_path": "DEVICE_001",
      "tipo": "CAMARA",
      "activa": true
    }
  ]
}
```

### 10. Obtener Estado en Vivo de Cámara

**GET** `/api/camaras/1/live_status/`

Response:
```json
{
  "camara_id": 1,
  "camara_nombre": "Cámara 1",
  "status": {
    "temp": 2.5,
    "state": "NORMAL",
    "ts": 1733702400000
  }
}
```

### 11. Crear Cámara (Solo ADMIN)

**POST** `/api/camaras/`

Request:
```json
{
  "sucursal": 1,
  "nombre": "Cámara 3",
  "codigo": "CAM-003",
  "firebase_path": "DEVICE_003",
  "tipo": "CAMARA",
  "activa": true
}
```

### 12. Listar Eventos

**GET** `/api/eventos/`

Query params opcionales:
- `camara_id`: Filtrar por cámara
- `tipo`: Filtrar por tipo (DESHIELO_N, DESHIELO_P, FALLA, etc.)
- `estado`: Filtrar por estado (DETECTADO, EN_CURSO, RESUELTO)
- `fecha_desde`: Filtrar desde fecha (YYYY-MM-DD)
- `fecha_hasta`: Filtrar hasta fecha (YYYY-MM-DD)

Response:
```json
{
  "count": 10,
  "results": [
    {
      "id": 123,
      "created_at": "2025-12-08T10:30:00Z",
      "camara": 1,
      "camara_nombre": "Cámara 1",
      "sucursal_nombre": "Sucursal Centro",
      "sucursal_id": 1,
      "fecha_inicio": "2025-12-08T10:30:00Z",
      "fecha_fin": "2025-12-08T11:00:00Z",
      "duracion_minutos": 30,
      "temp_max_c": "8.50",
      "tipo": "DESHIELO_N",
      "estado": "RESUELTO",
      "observaciones": null
    }
  ]
}
```

### 13. Obtener Eventos Recientes (últimas 24h)

**GET** `/api/eventos/recientes/`

Response: Igual que listar eventos, pero filtrado por últimas 24 horas.

### 14. Obtener Eventos en Curso

**GET** `/api/eventos/en_curso/`

Response: Eventos que no tienen `fecha_fin`.

### 15. Actualizar Evento (Agregar Observaciones)

**PATCH** `/api/eventos/123/`

Request:
```json
{
  "observaciones": "Se revisó la cámara y se encontró que la puerta estaba abierta"
}
```

### 16. Listar Lecturas de Temperatura

**GET** `/api/lecturas/temperaturas/`

Query params opcionales:
- `camara_id`: Filtrar por cámara
- `fecha_desde`: Filtrar desde fecha (YYYY-MM-DD)
- `fecha_hasta`: Filtrar hasta fecha (YYYY-MM-DD)

Response:
```json
{
  "count": 100,
  "results": [
    {
      "id": 1,
      "created_at": "2025-12-08T10:00:00Z",
      "camara": 1,
      "timestamp": "2025-12-08T10:00:00Z",
      "temperatura_c": "2.50",
      "origen": "firebase:controles"
    }
  ]
}
```

### 17. Listar Resúmenes Diarios

**GET** `/api/lecturas/resumen-diario/`

Query params opcionales:
- `camara_id`: Filtrar por cámara
- `fecha_desde`: Filtrar desde fecha (YYYY-MM-DD)
- `fecha_hasta`: Filtrar hasta fecha (YYYY-MM-DD)

Response:
```json
{
  "count": 7,
  "results": [
    {
      "id": 1,
      "created_at": "2025-12-08T00:00:00Z",
      "fecha": "2025-12-08",
      "camara": 1,
      "camara_nombre": "Cámara 1",
      "sucursal_nombre": "Sucursal Centro",
      "temp_min": "1.50",
      "temp_max": "3.20",
      "temp_promedio": "2.35",
      "total_lecturas": 96,
      "alertas_descongelamiento": 2,
      "fallas_detectadas": 0
    }
  ]
}
```

### 18. Listar Usuarios (Solo ADMIN)

**GET** `/api/users/`

Query params opcionales:
- `sucursal_id`: Filtrar por sucursal
- `rol`: Filtrar por rol

Response:
```json
{
  "count": 5,
  "results": [
    {
      "id": 1,
      "created_at": "2025-01-01T00:00:00Z",
      "firebase_uid": "abc123",
      "email": "admin@example.com",
      "nombre": "Juan Pérez",
      "rol": "ADMIN",
      "sucursal": null,
      "sucursal_data": null,
      "activo": true
    }
  ]
}
```

### 19. Crear Usuario (Solo ADMIN)

**POST** `/api/users/`

Request:
```json
{
  "firebase_uid": "xyz789",
  "email": "encargado@example.com",
  "nombre": "María González",
  "rol": "ENCARGADO",
  "sucursal": 1,
  "activo": true
}
```

### 20. Actualizar Usuario (Solo ADMIN)

**PUT** `/api/users/2/`

Request:
```json
{
  "firebase_uid": "xyz789",
  "email": "encargado@example.com",
  "nombre": "María González Actualizada",
  "rol": "ENCARGADO",
  "sucursal": 1,
  "activo": true
}
```

## Códigos de Estado HTTP

- `200 OK`: Operación exitosa
- `201 Created`: Recurso creado exitosamente
- `400 Bad Request`: Datos inválidos
- `401 Unauthorized`: No autenticado o token inválido
- `403 Forbidden`: No tiene permisos para esta operación
- `404 Not Found`: Recurso no encontrado
- `500 Internal Server Error`: Error del servidor

## Ejemplos con cURL

### Verificar Token

```bash
curl -X POST http://localhost:8000/api/auth/verify-token/ \
  -H "Content-Type: application/json" \
  -d '{"token": "eyJhbGciOiJSUzI1NiIsImtpZCI6..."}'
```

### Obtener KPIs

```bash
curl -X GET http://localhost:8000/api/dashboard/kpis/ \
  -H "Authorization: Bearer <token>"
```

### Listar Sucursales

```bash
curl -X GET http://localhost:8000/api/sucursales/ \
  -H "Authorization: Bearer <token>"
```

### Crear Sucursal

```bash
curl -X POST http://localhost:8000/api/sucursales/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "nombre": "Sucursal Norte",
    "direccion": "Calle Norte 456",
    "descripcion": "Sucursal zona norte",
    "activa": true
  }'
```

### Listar Eventos con Filtros

```bash
curl -X GET "http://localhost:8000/api/eventos/?tipo=DESHIELO_N&fecha_desde=2025-12-01" \
  -H "Authorization: Bearer <token>"
```

## Ejemplos con JavaScript (Axios)

### Configurar Axios

```javascript
import axios from 'axios';
import { auth } from './firebase';

const api = axios.create({
  baseURL: 'http://localhost:8000/api',
});

// Interceptor para agregar token
api.interceptors.request.use(async (config) => {
  const user = auth.currentUser;
  if (user) {
    const token = await user.getIdToken();
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});
```

### Obtener KPIs

```javascript
const response = await api.get('/dashboard/kpis/');
console.log(response.data);
```

### Crear Sucursal

```javascript
const nuevaSucursal = {
  nombre: 'Sucursal Norte',
  direccion: 'Calle Norte 456',
  descripcion: 'Sucursal zona norte',
  activa: true
};

const response = await api.post('/sucursales/', nuevaSucursal);
console.log(response.data);
```

### Listar Eventos con Filtros

```javascript
const response = await api.get('/eventos/', {
  params: {
    tipo: 'DESHIELO_N',
    fecha_desde: '2025-12-01',
    fecha_hasta: '2025-12-08'
  }
});
console.log(response.data.results);
```

## Paginación

Los endpoints que retornan listas usan paginación automática (50 items por página):

```json
{
  "count": 150,
  "next": "http://localhost:8000/api/eventos/?page=2",
  "previous": null,
  "results": [...]
}
```

Para obtener la siguiente página:

```javascript
const response = await api.get('/eventos/?page=2');
```

## Manejo de Errores

```javascript
try {
  const response = await api.get('/dashboard/kpis/');
  console.log(response.data);
} catch (error) {
  if (error.response) {
    // El servidor respondió con un código de error
    console.error('Error:', error.response.status);
    console.error('Mensaje:', error.response.data);
  } else if (error.request) {
    // La request se hizo pero no hubo respuesta
    console.error('No hay respuesta del servidor');
  } else {
    // Error al configurar la request
    console.error('Error:', error.message);
  }
}
```
