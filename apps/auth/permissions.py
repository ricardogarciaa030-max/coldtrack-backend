"""
Permisos personalizados para ColdTrack

Define los permisos basados en roles:
- ADMIN: Acceso total
- ENCARGADO: Acceso a su sucursal
- SUBJEFE: Solo lectura de su sucursal
"""

from rest_framework import permissions


class IsAuthenticated(permissions.BasePermission):
    """
    Permiso que verifica que el usuario esté autenticado con Firebase.
    """
    
    def has_permission(self, request, view):
        """
        Verifica si el request tiene un usuario autenticado.
        
        Args:
            request: HttpRequest con firebase_user
            view: Vista que se está accediendo
        
        Returns:
            bool: True si está autenticado
        """
        return hasattr(request, 'firebase_user') and request.firebase_user is not None


class IsAdmin(permissions.BasePermission):
    """
    Permiso que solo permite acceso a usuarios con rol ADMIN.
    """
    
    def has_permission(self, request, view):
        """
        Verifica si el usuario es ADMIN.
        
        Args:
            request: HttpRequest con firebase_user
            view: Vista que se está accediendo
        
        Returns:
            bool: True si es ADMIN
        """
        if not hasattr(request, 'firebase_user') or request.firebase_user is None:
            return False
        
        return request.firebase_user.get('rol') == 'ADMIN'


class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Permiso que permite lectura a todos los autenticados,
    pero solo ADMIN puede crear/editar/eliminar.
    """
    
    def has_permission(self, request, view):
        """
        Verifica permisos según el método HTTP.
        
        Args:
            request: HttpRequest con firebase_user
            view: Vista que se está accediendo
        
        Returns:
            bool: True si tiene permiso
        """
        if not hasattr(request, 'firebase_user') or request.firebase_user is None:
            return False
        
        # Métodos de lectura permitidos para todos
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Métodos de escritura solo para ADMIN
        return request.firebase_user.get('rol') == 'ADMIN'


class CanAccessSucursal(permissions.BasePermission):
    """
    Permiso que verifica si el usuario puede acceder a una sucursal específica.
    
    - ADMIN: Puede acceder a todas las sucursales
    - ENCARGADO/SUBJEFE: Solo puede acceder a su sucursal asignada
    """
    
    def has_permission(self, request, view):
        """
        Verifica si el usuario está autenticado.
        """
        return hasattr(request, 'firebase_user') and request.firebase_user is not None
    
    def has_object_permission(self, request, view, obj):
        """
        Verifica si el usuario puede acceder al objeto (sucursal).
        
        Args:
            request: HttpRequest con firebase_user
            view: Vista que se está accediendo
            obj: Objeto sucursal
        
        Returns:
            bool: True si puede acceder
        """
        user = request.firebase_user
        
        # ADMIN puede acceder a todo
        if user.get('rol') == 'ADMIN':
            return True
        
        # ENCARGADO y SUBJEFE solo a su sucursal
        return obj.id == user.get('sucursal_id')


class CanEditSucursal(permissions.BasePermission):
    """
    Permiso que verifica si el usuario puede editar una sucursal.
    
    - ADMIN: Puede editar todas las sucursales
    - ENCARGADO: Puede editar su sucursal
    - SUBJEFE: Solo lectura
    """
    
    def has_permission(self, request, view):
        """
        Verifica si el usuario está autenticado.
        """
        return hasattr(request, 'firebase_user') and request.firebase_user is not None
    
    def has_object_permission(self, request, view, obj):
        """
        Verifica si el usuario puede editar el objeto.
        
        Args:
            request: HttpRequest con firebase_user
            view: Vista que se está accediendo
            obj: Objeto a editar
        
        Returns:
            bool: True si puede editar
        """
        user = request.firebase_user
        
        # Lectura permitida para todos (ya validado por CanAccessSucursal)
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # ADMIN puede editar todo
        if user.get('rol') == 'ADMIN':
            return True
        
        # ENCARGADO puede editar su sucursal
        if user.get('rol') == 'ENCARGADO':
            return obj.sucursal_id == user.get('sucursal_id')
        
        # SUBJEFE no puede editar
        return False


def filter_by_sucursal(queryset, user):
    """
    Filtra un queryset según la sucursal del usuario.
    
    Función auxiliar para aplicar filtros de sucursal en las vistas.
    
    Args:
        queryset: QuerySet de Django a filtrar
        user: Diccionario con datos del usuario (firebase_user)
    
    Returns:
        QuerySet filtrado
    
    Example:
        >>> from apps.auth.permissions import filter_by_sucursal
        >>> camaras = CamaraFrio.objects.all()
        >>> camaras = filter_by_sucursal(camaras, request.firebase_user)
    """
    # ADMIN ve todo
    if user.get('rol') == 'ADMIN':
        return queryset
    
    # ENCARGADO y SUBJEFE solo ven su sucursal
    sucursal_id = user.get('sucursal_id')
    if sucursal_id:
        return queryset.filter(sucursal_id=sucursal_id)
    
    # Si no tiene sucursal asignada, no ve nada
    return queryset.none()
