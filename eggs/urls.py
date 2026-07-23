from django.urls import path
from . import views

urlpatterns = [
    # path('market/search-pets/', views.search_pets, name='search_pets'),
    path('hatch/', views.hatch_lookup, name='hatch_lookup'),
    # path('market/', views.market, name='market'),
    # path('market/publish/', views.publish_trade, name='publish_trade'),
    # path('market/my/', views.my_trades, name='my_trades'),
    # path('market/edit/<int:trade_id>/', views.edit_trade, name='edit_trade'),
    # path('market/delist/<int:trade_id>/', views.delist_trade, name='delist_trade'),
]
