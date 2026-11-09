from django.contrib import admin
from django.urls import path,include
from apps.core import views

app_name = 'core'

urlpatterns = [
    path('', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('change-password/', views.change_password_view, name='change_password'),
    path('verify-otp/', views.verify_otp_view, name='verify_otp'),
]
