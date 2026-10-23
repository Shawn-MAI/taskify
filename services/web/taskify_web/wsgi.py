"""WSGI entry point for the Taskify web service."""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "taskify_web.settings")
application = get_wsgi_application()
