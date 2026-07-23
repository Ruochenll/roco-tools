from django.urls import path
from . import views

urlpatterns = [
    path('', views.pet_list, name='pet_list'),
    path('<int:pet_id>/', views.pet_detail, name='pet_detail'),
]
