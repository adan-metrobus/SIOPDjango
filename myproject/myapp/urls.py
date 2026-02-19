from django.urls import path
from . import views

urlpatterns = [
    path("", views.grafica_global_siop, name="grafica_global_siop"),
    path('detalle-tritones/', views.detalle_tritones_trimestre_view, name='detalle_tritones_trimestre'),
    path('legacy-index/', views.index, name="index"),
    path('status-abierto/', views.grafica_status_abierto, name='grafica_status_abierto'),
    path('causas-otros/', views.grafica_causas_otros, name='grafica_causas_otros'),
]
