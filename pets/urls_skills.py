from django.urls import path
from . import views

app_name = 'skills'

urlpatterns = [
    path('', views.skill_list, name='skill_list'),
    path('<int:skill_id>/', views.skill_detail, name='skill_detail'),
]
