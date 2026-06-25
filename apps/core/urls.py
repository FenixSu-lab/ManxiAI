"""URL routes for public core diagnostics."""

from django.urls import path

from .views import dashboard_summary, health_check

urlpatterns = [
    path('dashboard/summary/', dashboard_summary, name='dashboard-summary'),
    path('health/', health_check, name='health-check'),
]
