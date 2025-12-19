-- Script para deshabilitar RLS temporalmente
-- Ejecutar en el SQL Editor de Supabase

-- Deshabilitar RLS en todas las tablas
ALTER TABLE usuarios DISABLE ROW LEVEL SECURITY;
ALTER TABLE sucursales DISABLE ROW LEVEL SECURITY;
ALTER TABLE camaras_frio DISABLE ROW LEVEL SECURITY;
ALTER TABLE lecturas_temperatura DISABLE ROW LEVEL SECURITY;
ALTER TABLE eventos_temperatura DISABLE ROW LEVEL SECURITY;
ALTER TABLE resumen_diario_camara DISABLE ROW LEVEL SECURITY;

-- Verificar el estado de RLS
SELECT 
    schemaname,
    tablename,
    rowsecurity
FROM pg_tables 
WHERE schemaname = 'public'
ORDER BY tablename;