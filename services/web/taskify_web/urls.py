"""Root URL configuration: all routes live in the ``boards`` app."""

from django.urls import include, path

urlpatterns = [path("", include("boards.urls"))]
