"""Modelos de Eventos - Mapea tabla eventos_temperatura de Supabase"""

from django.db import models
from apps.camaras.models import CamaraFrio


class EventoTemperatura(models.Model):
    """Eventos de temperatura (deshielos, fallas, etc.)"""
    
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField(auto_now_add=True)
    camara = models.ForeignKey(CamaraFrio, on_delete=models.CASCADE, db_column='camara_id')
    fecha_inicio = models.DateTimeField()
    fecha_fin = models.DateTimeField(null=True, blank=True)
    duracion_minutos = models.BigIntegerField(null=True, blank=True)
    temp_max_c = models.DecimalField(max_digits=5, decimal_places=2)
    tipo = models.TextField()  # DESHIELO_N, DESHIELO_P, FALLA, FALLA_EN_CURSO
    estado = models.TextField()  # DETECTADO, EN_CURSO, RESUELTO
    observaciones = models.TextField(null=True, blank=True)
    
    class Meta:
        db_table = 'eventos_temperatura'
        managed = False
        ordering = ['-fecha_inicio']
    
    def __str__(self):
        return f"{self.tipo} - {self.camara.nombre} ({self.fecha_inicio})"
