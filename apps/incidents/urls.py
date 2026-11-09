from django.urls import path
from . import views


app_name = 'incidents'

urlpatterns = [
    path('', views.index, name='index'),
    path('export/', views.export_incidents_csv, name='export_csv'),
    path('<int:incident_id>/', views.detail, name='detail'),
    path('resolve/<int:incident_id>/', views.resolve_incident, name='resolve_incident'),
    
]
