from django.urls import path
from . import views_damage, views_team  # , views_capture

app_name = 'pvp'

urlpatterns = [
    path('damage-calc/', views_damage.damage_calc, name='damage_calc'),
    path('damage-calc/stat-card/', views_damage.pet_stat_card, name='pet_stat_card'),
    path('damage-calc/skills/', views_damage.pet_skills, name='pet_skills'),
    path('damage-calc/damages/', views_damage.calc_damages, name='calc_damages'),
    path('pet-search/', views_damage.pet_search, name='pet_search'),
    # path('capture/', views_capture.capture_page, name='capture_page'),      # 截图识别暂关
    # path('capture/analyze/', views_capture.capture_analyze, name='capture_analyze'),

    # PVP计算器
    path('battle-calc/', views_team.battle_calc, name='battle_calc'),
    path('battle-calc/import-roster/', views_team.api_import_roster, name='api_import_roster'),
    path('battle-calc/load-team/<int:team_id>/', views_team.api_popular_team, name='api_popular_team'),
    path('battle-calc/pet-search/', views_team.api_pet_search, name='api_pet_search'),
]
