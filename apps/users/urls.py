from django.contrib import admin
from django.urls import path,include
from apps.users import views

app_name = 'users'

urlpatterns = [
    path('', views.index, name='index'),
    path('add/', views.add_user, name='add_user'),
    path('update/<int:user_id>/', views.update_user, name='update_user'),
    path('delete/', views.delete_user, name='delete_user'),

]