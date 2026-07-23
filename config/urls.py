from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('core.urls')),
    # path('accounts/', include('accounts.urls')),  # 登录注册暂关
    path('pets/', include('pets.urls')),
    path('skills/', include('pets.urls_skills')),
    path('type-calc/', include('pets.urls_calc')),
    path('eggs/', include('eggs.urls')),
    path('articles/', include('articles.urls')),
    path('pvp/', include('pvp_assistant.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
