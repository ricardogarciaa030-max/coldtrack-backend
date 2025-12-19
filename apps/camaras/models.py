"""Modelos de Cámaras de Frío - Mapea tabla camaras_frio de Supabase"""

from django.db import models
from apps.sucursales.models import Sucursal


class CamaraFrio(models.Model):
    """Modelo que representa una cámara de frío"""
    
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField(auto_now_add=True)
    sucursal = models.ForeignKey(Sucursal, on_delete=models.CASCADE, db_column='sucursal_id')
    nombre = models.TextField()
    codigo = models.TextField(blank=True, null=True)
    firebase_path = models.TextField()  # device_id en Firebase
    tipo = models.TextField(default='CAMARA')  # CAMARA, CAMION, BODEGA
    activa = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'camaras_frio'
        managed = False
        ordering = ['nombre']
    
    def __str__(self):
        return f"{self.nombre} ({self.codigo})"
