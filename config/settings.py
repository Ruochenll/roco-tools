import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'django-insecure-roco-kingdom-world-dev-key-change-in-prod'

DEBUG = True

ALLOWED_HOSTS = ['*']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Third-party
    'ckeditor',
    # Project apps
    'core',
    'accounts',
    'pets',
    'eggs',
    'articles',
    'pvp_assistant',
    'items',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# Django 4.1+ 开发模式也默认缓存模板,导致改模板必须重启服务才生效。
# DEBUG 下关闭模板缓存:改完模板刷新浏览器即可看到效果。
if DEBUG:
    TEMPLATES[0]['APP_DIRS'] = False
    TEMPLATES[0]['OPTIONS']['loaders'] = [
        'django.template.loaders.filesystem.Loader',
        'django.template.loaders.app_directories.Loader',
    ]

WSGI_APPLICATION = 'config.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'zh-hans'
TIME_ZONE = 'Asia/Shanghai'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'

# ===== 远行商人第三方数据源(apii.xianyuw.cn,免费但需注册获取 key) =====
# 推荐通过环境变量配置: set MERCHANT_API_KEY=xxxx
MERCHANT_API_URL = os.environ.get('MERCHANT_API_URL', 'https://apii.xianyuw.cn/api/v1/rocom-merchant')
MERCHANT_API_KEY = os.environ.get('MERCHANT_API_KEY', '')

# 到点(8/12/16/20)自动拉取:后台线程,失败重试
MERCHANT_AUTO_FETCH = True          # 关掉则只剩首页懒加载 + 手动命令
MERCHANT_FETCH_RETRIES = 5          # 每个刷新点最多尝试次数
MERCHANT_FETCH_RETRY_INTERVAL = 5   # 重试间隔(秒)

CKEDITOR_CONFIGS = {
    'default': {
        'toolbar': 'full',
        'height': 400,
        'width': '100%',
        'language': 'zh-cn',
    },
}

# ===== 本地私有配置(config/settings_local.py,已加入 .gitignore) =====
# 可覆盖本文件中的任意配置,例如 MERCHANT_API_KEY
try:
    from .settings_local import *  # noqa: F401,F403
except ImportError:
    pass
