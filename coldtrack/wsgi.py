"""
WSGI config for ColdTrack project.

Expone el callable WSGI como una variable a nivel de módulo llamada ``application``.
Se usa para deployment en servidores de producción.
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'coldtrack.settings')

application = get_wsgi_application()
