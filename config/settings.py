import os
from pathlib import Path
from datetime import timedelta
from dotenv import load_dotenv
from django.core.exceptions import ImproperlyConfigured
from decouple import config
import dj_database_url

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

DEBUG = os.getenv('DJANGO_DEBUG', 'False').lower() in ['true', '1', 'yes']
# DEBUG = os.getenv("DEBUG", "False").lower() in ["true", "1", "yes"]
# SECRET_KEY = os.getenv('DJANGO_SECRET_KEY')
# SECRET_KEY = config("SECRET_KEY")
# if not SECRET_KEY:
#     if DEBUG:
#         SECRET_KEY = 'django-insecure-vetlink-kano-dev-key'
#     else:
#         raise ImproperlyConfigured('The DJANGO_SECRET_KEY environment variable must be set in production.')

SECRET_KEY = config(
    "SECRET_KEY",
    default="django-insecure-vetlink-kano-dev-key"
)

# allowed_hosts = os.getenv('ALLOWED_HOSTS')
# if allowed_hosts:
#     ALLOWED_HOSTS = [host.strip() for host in allowed_hosts.split(',') if host.strip()]
# else:
#     ALLOWED_HOSTS = ['localhost', '127.0.0.1'] if DEBUG else []

ALLOWED_HOSTS = [
    "localhost",
    "127.0.0.1",
    ".onrender.com",
]


#CORS_ALLOW_ALL_ORIGINS = os.getenv('CORS_ALLOW_ALL_ORIGINS', 'True' if DEBUG else 'False').lower() in ['true', '1', 'yes']
#CORS_ALLOW_CREDENTIALS = os.getenv('CORS_ALLOW_CREDENTIALS', 'True' if DEBUG else 'False').lower() in ['true', '1', 'yes']

CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "https://vetlinkfrontendkan-git-main-mevs-me.vercel.app",
    "https://vetlinkfrontendkan-coikas6hd-mevs-me.vercel.app",
]

CORS_ALLOW_CREDENTIALS = True

CSRF_TRUSTED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "https://vetlinkfrontendkan-git-main-mevs-me.vercel.app",
    "https://vetlinkfrontendkan-coikas6hd-mevs-me.vercel.app",
]

SECURE_HSTS_SECONDS = int(os.getenv('SECURE_HSTS_SECONDS', '0' if DEBUG else '31536000'))
SECURE_HSTS_INCLUDE_SUBDOMAINS = os.getenv('SECURE_HSTS_INCLUDE_SUBDOMAINS', 'False' if DEBUG else 'True').lower() in ['true', '1', 'yes']
SECURE_HSTS_PRELOAD = os.getenv('SECURE_HSTS_PRELOAD', 'False' if DEBUG else 'True').lower() in ['true', '1', 'yes']
SECURE_SSL_REDIRECT = os.getenv('SECURE_SSL_REDIRECT', 'False' if DEBUG else 'True').lower() in ['true', '1', 'yes']
SESSION_COOKIE_SECURE = os.getenv('SESSION_COOKIE_SECURE', 'False' if DEBUG else 'True').lower() in ['true', '1', 'yes']
CSRF_COOKIE_SECURE = os.getenv('CSRF_COOKIE_SECURE', 'False' if DEBUG else 'True').lower() in ['true', '1', 'yes']
SECURE_CONTENT_TYPE_NOSNIFF = os.getenv('SECURE_CONTENT_TYPE_NOSNIFF', 'False' if DEBUG else 'True').lower() in ['true', '1', 'yes']
SECURE_BROWSER_XSS_FILTER = os.getenv('SECURE_BROWSER_XSS_FILTER', 'False' if DEBUG else 'True').lower() in ['true', '1', 'yes']
SECURE_REFERRER_POLICY = os.getenv('SECURE_REFERRER_POLICY', 'strict-origin-when-cross-origin')
X_FRAME_OPTIONS = os.getenv('X_FRAME_OPTIONS', 'DENY')
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# In production, the app should explicitly opt into permissive CORS and secure cookies.
# Local development can use the default permissive settings without needing env vars.
if not DEBUG:
    CORS_ALLOW_ALL_ORIGINS = False

AUTH_USER_MODEL = 'accounts.User'

INSTALLED_APPS = [
    'daphne',  # must come before django.contrib.staticfiles for runserver WebSocket support
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third-party apps
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'corsheaders',
    'django_filters',
    'drf_spectacular',
    'channels',

    # Local apps
    'apps.core',
    'apps.community',
    'apps.marketplace',
    'apps.payments',
    'apps.accounts',
    'apps.veterinarians',
    'apps.patients',
    'apps.appointments',
    'apps.consultations',
    'apps.pharmacy',
    'apps.laboratory',
    'apps.surveillance',
    'apps.billing',
    'apps.clinical_notes',
    'apps.notifications',
    'apps.farmers',
    'apps.chat',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # Thread-local request middleware (for audit logging)
    'apps.core.middleware.ThreadLocalMiddleware',
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

WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'

# Channels channel layer. Redis when REDIS_URL is set (production); otherwise an
# in-memory layer keeps local single-process development working out of the box.
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels.layers.InMemoryChannelLayer',
    },
}

REDIS_URL = os.getenv('REDIS_URL', '')
if REDIS_URL:
    CHANNEL_LAYERS['default'] = {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {'hosts': [REDIS_URL]},
    }

# Chat security constants
MAX_UPLOAD_SIZE = int(os.getenv('CHAT_MAX_UPLOAD_SIZE', 8 * 1024 * 1024))  # 8 MB per file
CHAT_ALLOWED_UPLOADS = (
    'image/jpeg', 'image/png', 'image/webp', 'image/gif',
    'video/mp4', 'application/pdf',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
)

DATABASES = {
    "default": dj_database_url.parse(
        config("DATABASE_URL"),
        conn_max_age=600,
        ssl_require=True,
    )
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Africa/Lagos'
USE_I18N = True
USE_TZ = True

STATIC_ROOT = BASE_DIR / "staticfiles"

STATICFILES_STORAGE = (
    "whitenoise.storage.CompressedManifestStaticFilesStorage"
)
STATIC_URL = '/static/'
# STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# ============================================================
# STATIC FILES
# ============================================================

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# CORS Settings
# Values are configured above based on debug mode or explicit environment variables.
# Default behavior: allow all origins during local development and disable in production.

# Django REST Framework Settings
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 100,
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

# Throttling to limit brute-force attempts (including token obtain)
REST_FRAMEWORK.setdefault('DEFAULT_THROTTLE_CLASSES', [
    'rest_framework.throttling.AnonRateThrottle',
    'rest_framework.throttling.UserRateThrottle',
    'rest_framework.throttling.ScopedRateThrottle',
])
REST_FRAMEWORK.setdefault('DEFAULT_THROTTLE_RATES', {
    'anon': '10/min',
    'user': '1000/day',
    'auth': '5/min',
})

# SimpleJWT Settings
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(days=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
}

# DRF Spectacular OpenAPI documentation settings
SPECTACULAR_SETTINGS = {
    'TITLE': 'VetLink Kano REST API',
    'DESCRIPTION': 'Enterprise One Health Veterinary Management & Epidemiological Surveillance Platform API',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
}

FLUTTERWAVE_SECRET_KEY = os.getenv('FLUTTERWAVE_SECRET_KEY', '')
FLUTTERWAVE_PUBLIC_KEY = os.getenv('FLUTTERWAVE_PUBLIC_KEY', '')
FLUTTERWAVE_API_BASE = os.getenv('FLUTTERWAVE_API_BASE', 'https://api.flutterwave.com/v3')
FLUTTERWAVE_WEBHOOK_SECRET = os.getenv('FLUTTERWAVE_WEBHOOK_SECRET', FLUTTERWAVE_SECRET_KEY)
