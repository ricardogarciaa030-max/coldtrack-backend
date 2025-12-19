"""
Modelos de Sucursales

Mapea la tabla 'sucursales' de Supabase.
NO crea la tabla, solo la mapea para usar con Django ORM.
"""

from django.db import models


class Sucursal(models.Model):
    """
    Modelo que representa una sucursal.
    
    Mapea la tabla 'sucursales' en Supabase PostgreSQL.
    
    Campos:
        id: ID único de la sucursal
        created_at: Fecha de creación
        nombre: Nombre de la sucursal
        direccion: Dirección física
        descripcion: Descripción adicional
        activa: Si la sucursal está activa
    """
    
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField(auto_now_add=True)
    nombre = models.TextField()
    direccion = models.TextField(blank=True, null=True)
    descripcion = models.TextField(blank=True, null=True)
    activa = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'sucursales'
        managed = False  # Django no gestiona esta tabla
        ordering = ['nombre']
    
    def __str__(self):
        return self.nombre
