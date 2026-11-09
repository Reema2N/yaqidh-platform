from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.index, name='index'),
    path('api/live/', views.dashboard_live_api, name='dashboard_live_api'),
]