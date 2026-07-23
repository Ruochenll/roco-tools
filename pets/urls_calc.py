from django.urls import path
from . import views

urlpatterns = [
    path('', views.type_calc, name='type_calc'),
]
