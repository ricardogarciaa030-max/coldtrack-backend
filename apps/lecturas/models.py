"""Modelos de Lecturas y Resúmenes - Mapea tablas de Supabase"""

from django.db import models
from apps.camaras.models import CamaraFrio


class LecturaTemperatura(models.Model):
    """Lecturas individuales de temperatura"""
    
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField(auto_now_add=True)
    camara = models.ForeignKey(CamaraFrio, on_delete=models.CASCADE, db_column='camara_id')
    timestamp = models.DateTimeField()
    temperatura_c = models.DecimalField(max_digits=5, decimal_places=2)
    origen = models.TextField()  # firebase:status, firebase:controles
    
    class Meta:
        db_table = 'lecturas_temperatura'
        managed = False
        ordering = ['-timestamp']


class ResumenDiarioCamara(models.Model):
    """Resumen diario de temperaturas por cámara"""
    
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField(auto_now_add=True)
    fecha = models.DateField()
    camara = models.ForeignKey(CamaraFrio, on_delete=models.CASCADE, db_column='camara_id')
    temp_min = models.DecimalField(max_digits=5, decimal_places=2)
    temp_max = models.DecimalField(max_digits=5, decimal_places=2)
    temp_promedio = models.DecimalField(max_digits=5, decimal_places=2)
    total_lecturas = models.BigIntegerField()
    alertas_descongelamiento = models.BigIntegerField(default=0)
    fallas_detectadas = models.BigIntegerField(default=0)
    
    class Meta:
        db_table = 'resumen_diario_camara'
        managed = False
        ordering = ['-fecha']
        unique_together = [['fecha', 'camara']]
