from django.urls import path
from . import views

urlpatterns = [
    path("", views.grafica_global_siop, name="grafica_global_siop"),
    path('detalle-tritones/', views.detalle_tritones_trimestre_view, name='detalle_tritones_trimestre'),
]
