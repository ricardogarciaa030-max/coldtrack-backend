"""Modelos de Usuarios - Mapea tabla usuarios de Supabase"""

from django.db import models
from apps.sucursales.models import Sucursal


class Usuario(models.Model):
    """Modelo que representa un usuario del sistema"""
    
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField(auto_now_add=True)
    firebase_uid = models.TextField(unique=True)
    email = models.TextField()
    nombre = models.TextField()
    rol = models.TextField()  # ADMIN, ENCARGADO, SUBJEFE
    sucursal = models.ForeignKey(Sucursal, on_delete=models.SET_NULL, 
                                  null=True, blank=True, db_column='sucursal_id')
    activo = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'usuarios'
        managed = False
        ordering = ['nombre']
    
    def __str__(self):
        return f"{self.nombre} ({self.rol})"
