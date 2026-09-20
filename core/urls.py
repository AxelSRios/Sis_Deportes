"""
Rutas de la aplicación core (Sistema de Gestión Deportiva AFO · Oruro).
"""
from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('panel-general/', views.panel, name='panel'),
    path('clubes-equipos/', views.clubes, name='clubes'),
    path('campeonatos-fixture/', views.campeonatos, name='campeonatos'),
    path('arbitraje-designaciones/', views.arbitraje, name='arbitraje'),
    path('deportistas-fichajes/', views.deportistas, name='deportistas'),
    path('tesoreria-pagos/', views.tesoreria, name='tesoreria'),
    path('auditoria-usuarios/', views.auditoria, name='auditoria'),
]