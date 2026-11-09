from django.contrib import admin
from django.urls import path,include
from apps.live_monitoring import views

app_name = 'live_monitoring'

urlpatterns = [
    path('', views.index, name='index'),
]