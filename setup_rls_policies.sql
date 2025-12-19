-- ============================================================================
-- CONFIGURACIÓN DE POLÍTICAS RLS PARA COLDTRACK
-- ============================================================================
-- Este script configura las políticas de Row Level Security (RLS) en Supabase
-- para permitir que la aplicación funcione correctamente.
--
-- IMPORTANTE: Ejecuta este script en el SQL Editor de Supabase
-- URL: https://supabase.com/dashboard/project/spzuykuhcunyohyilnem/sql
-- ============================================================================

-- ============================================================================
-- TABLA: usuarios
-- ============================================================================
-- Habilitar RLS
ALTER TABLE usuarios ENABLE ROW LEVEL SECURITY;

-- Eliminar políticas existentes si existen
DROP POLICY IF EXISTS "Permitir lectura de usuarios activos" ON usuarios;
DROP POLICY IF EXISTS "Permitir lectura de usuarios" ON usuarios;

-- Política para permitir SELECT (lectura) de usuarios activos
-- Esto permite que el backend pueda buscar usuarios durante el login
CREATE POLICY "Permitir lectura de usuarios activos"
ON usuarios
FOR SELECT
USING (activo = true);

-- Nota: INSERT/UPDATE/DELETE solo se permiten con service_role key
-- (esto ya está configurado por defecto en Supabase)

-- ============================================================================
-- TABLA: sucursales
-- ============================================================================
ALTER TABLE sucursales ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Permitir lectura de sucursales activas" ON sucursales;
DROP POLICY IF EXISTS "Permitir lectura de sucursales" ON sucursales;

CREATE POLICY "Permitir lectura de sucursales activas"
ON sucursales
FOR SELECT
USING (activa = true);

-- ============================================================================
-- TABLA: camaras_frio
-- ============================================================================
ALTER TABLE camaras_frio ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Permitir lectura de cámaras activas" ON camaras_frio;
DROP POLICY IF EXISTS "Permitir lectura de cámaras" ON camaras_frio;

CREATE POLICY "Permitir lectura de cámaras activas"
ON camaras_frio
FOR SELECT
USING (activa = true);

-- ============================================================================
-- TABLA: lecturas_temperatura
-- ============================================================================
ALTER TABLE lecturas_temperatura ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Permitir lectura de lecturas" ON lecturas_temperatura;

-- Permitir lectura de todas las lecturas
CREATE POLICY "Permitir lectura de lecturas"
ON lecturas_temperatura
FOR SELECT
USING (true);

-- Permitir inserción de lecturas (para el script de sincronización)
DROP POLICY IF EXISTS "Permitir inserción de lecturas" ON lecturas_temperatura;

CREATE POLICY "Permitir inserción de lecturas"
ON lecturas_temperatura
FOR INSERT
WITH CHECK (true);

-- ============================================================================
-- TABLA: eventos_temperatura
-- ============================================================================
ALTER TABLE eventos_temperatura ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Permitir lectura de eventos" ON eventos_temperatura;
DROP POLICY IF EXISTS "Permitir inserción de eventos" ON eventos_temperatura;
DROP POLICY IF EXISTS "Permitir actualización de eventos" ON eventos_temperatura;

-- Permitir lectura de todos los eventos
CREATE POLICY "Permitir lectura de eventos"
ON eventos_temperatura
FOR SELECT
USING (true);

-- Permitir inserción de eventos
CREATE POLICY "Permitir inserción de eventos"
ON eventos_temperatura
FOR INSERT
WITH CHECK (true);

-- Permitir actualización de eventos
CREATE POLICY "Permitir actualización de eventos"
ON eventos_temperatura
FOR UPDATE
USING (true);

-- ============================================================================
-- TABLA: resumen_diario_camara
-- ============================================================================
ALTER TABLE resumen_diario_camara ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Permitir lectura de resúmenes" ON resumen_diario_camara;
DROP POLICY IF EXISTS "Permitir inserción de resúmenes" ON resumen_diario_camara;
DROP POLICY IF EXISTS "Permitir actualización de resúmenes" ON resumen_diario_camara;

CREATE POLICY "Permitir lectura de resúmenes"
ON resumen_diario_camara
FOR SELECT
USING (true);

CREATE POLICY "Permitir inserción de resúmenes"
ON resumen_diario_camara
FOR INSERT
WITH CHECK (true);

CREATE POLICY "Permitir actualización de resúmenes"
ON resumen_diario_camara
FOR UPDATE
USING (true);

-- ============================================================================
-- VERIFICACIÓN
-- ============================================================================
-- Verifica que las políticas se hayan creado correctamente

SELECT 
    schemaname,
    tablename,
    policyname,
    permissive,
    roles,
    cmd,
    qual,
    with_check
FROM pg_policies
WHERE schemaname = 'public'
ORDER BY tablename, policyname;

-- ============================================================================
-- NOTAS IMPORTANTES
-- ============================================================================
-- 1. Estas políticas permiten lectura pública (con anon key) de datos
-- 2. La escritura (INSERT/UPDATE/DELETE) requiere service_role key
-- 3. Para mayor seguridad en producción, considera políticas más restrictivas
-- 4. Puedes agregar políticas basadas en el rol del usuario autenticado
-- 5. Las políticas se evalúan en orden, la primera que coincida se aplica
-- ============================================================================
