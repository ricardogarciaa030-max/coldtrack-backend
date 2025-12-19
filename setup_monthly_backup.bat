@echo off
REM Script para configurar respaldo mensual automático
REM Ejecutar este archivo para programar respaldos automáticos

echo ========================================
echo   CONFIGURACION DE RESPALDO MENSUAL
echo ========================================
echo.

echo 🗄️  Este script configurará respaldos automáticos para:
echo    - Proteger datos antes de que Firebase los borre
echo    - Mantener historial completo en Supabase
echo    - Ejecutar automáticamente cada fin de mes
echo.

echo 📅 Opciones disponibles:
echo    1. Respaldar mes actual (Diciembre 2025)
echo    2. Respaldar mes anterior 
echo    3. Configurar respaldo automático
echo    4. Verificar estado actual
echo.

set /p choice="Selecciona una opción (1-4): "

if "%choice%"=="1" (
    echo.
    echo 🚀 Respaldando mes actual...
    python backup_monthly_data.py current
    pause
) else if "%choice%"=="2" (
    echo.
    echo 🚀 Respaldando mes anterior...
    python backup_monthly_data.py previous
    pause
) else if "%choice%"=="3" (
    echo.
    echo ⚙️  Configurando respaldo automático...
    echo.
    echo Para configurar respaldo automático, agrega esta tarea al Programador de Tareas de Windows:
    echo.
    echo Comando: python backup_monthly_data.py schedule
    echo Frecuencia: Diaria (días 28-31 de cada mes)
    echo Ruta: %CD%
    echo.
    echo O ejecuta manualmente el último día de cada mes.
    pause
) else if "%choice%"=="4" (
    echo.
    echo 🔍 Verificando estado actual...
    python backup_monthly_data.py schedule
    pause
) else (
    echo Opción inválida
    pause
)

echo.
echo ✅ Proceso completado
pause