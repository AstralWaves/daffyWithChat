import os
from pathlib import Path
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-your-secret-key-here!')

DEBUG = os.getenv('DEBUG', 'True') == 'True'

ALLOWED_HOSTS = ['*']

INSTALLED_APPS = [
    'daphne',  # For ASGI support
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Third party
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
    'channels',
    'storages',
    
    # Local apps
    'apps.accounts',
    'apps.chat',
    'apps.calls',
    'apps.notifications',
    'apps.files',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'daffy_project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, '../frontend')],
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

WSGI_APPLICATION = 'daffy_project.wsgi.application'
ASGI_APPLICATION = 'daffy_project.asgi.application'

# ===================================================== 
# DATABASE CONFIGURATION 
# ===================================================== 

# Try to use PostgreSQL if configured, otherwise fallback to SQLite for local development
if os.getenv('DB_NAME') and os.getenv('DB_USER'):
    DATABASES = { 
        'default': { 
            'ENGINE': 'django.db.backends.postgresql', 
            'NAME': os.getenv('DB_NAME', 'daffy_chat_db'), 
            'USER': os.getenv('DB_USER', 'daffy_user'), 
            'PASSWORD': os.getenv('DB_PASSWORD', 'Daffy@Chat2024'), 
            'HOST': os.getenv('DB_HOST', 'localhost'), 
            'PORT': os.getenv('DB_PORT', '5432'), 
            'CONN_MAX_AGE': 60, 
            'OPTIONS': { 
                'connect_timeout': 10, 
                'keepalives': 1, 
                'keepalives_idle': 30, 
                'keepalives_interval': 10, 
                'keepalives_count': 5, 
            } 
        } 
    } 
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

if not DEBUG: 
    DATABASES['replica'] = { 
        'ENGINE': 'django.db.backends.postgresql', 
        'NAME': os.getenv('REPLICA_DB_NAME', 'daffy_chat_db_replica'), 
        'USER': os.getenv('REPLICA_DB_USER', 'daffy_replica_user'), 
        'PASSWORD': os.getenv('REPLICA_DB_PASSWORD', 'Daffy@Chat2024'), 
        'HOST': os.getenv('REPLICA_DB_HOST', 'localhost'), 
        'PORT': os.getenv('REPLICA_DB_PORT', '5433'), 
    } 
    
    DATABASE_ROUTERS = ['core.db_router.ReplicaRouter'] 

# ===================================================== 
# REDIS CONFIGURATION 
# ===================================================== 

REDIS_CONFIG = { 
    'host': os.getenv('REDIS_HOST', 'localhost'), 
    'port': int(os.getenv('REDIS_PORT', 6379)), 
    'password': os.getenv('REDIS_PASSWORD', 'Redis@2024'), 
    'db': int(os.getenv('REDIS_DB', 0)), 
    'decode_responses': True, 
    'socket_timeout': 5, 
    'socket_connect_timeout': 5, 
    'retry_on_timeout': True, 
} 

REDIS_SESSION_URL = f"redis://:{REDIS_CONFIG['password']}@{REDIS_CONFIG['host']}:{REDIS_CONFIG['port']}/0" 
REDIS_PRESENCE_URL = f"redis://:{REDIS_CONFIG['password']}@{REDIS_CONFIG['host']}:{REDIS_CONFIG['port']}/1" 
REDIS_QUEUE_URL = f"redis://:{REDIS_CONFIG['password']}@{REDIS_CONFIG['host']}:{REDIS_CONFIG['port']}/2" 
REDIS_CACHE_URL = f"redis://:{REDIS_CONFIG['password']}@{REDIS_CONFIG['host']}:{REDIS_CONFIG['port']}/3" 

# Redis Channel Layers for WebSockets
if os.getenv('REDIS_HOST'):
    CHANNEL_LAYERS = { 
        'default': { 
            'BACKEND': 'channels_redis.core.RedisChannelLayer', 
            'CONFIG': { 
                "hosts": [REDIS_PRESENCE_URL], 
                "symmetric_encryption_keys": [SECRET_KEY[:32]], 
                "capacity": 1500, 
                "expiry": 60, 
            }, 
        }, 
    } 
else:
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels.layers.InMemoryChannelLayer',
        },
    }

# Cache Configuration 
CACHES = { 
    'default': { 
        'BACKEND': 'django_redis.cache.RedisCache', 
        'LOCATION': REDIS_CACHE_URL, 
        'OPTIONS': { 
            'CLIENT_CLASS': 'django_redis.client.DefaultClient', 
            'PARSER_CLASS': 'redis.connection.HiredisParser', 
            'CONNECTION_POOL_CLASS': 'redis.BlockingConnectionPool', 
            'CONNECTION_POOL_CLASS_KWARGS': { 
                'max_connections': 50, 
                'timeout': 20, 
            }, 
            'MAX_CONNECTIONS': 1000, 
            'PICKLE_VERSION': -1, 
        }, 
        'KEY_PREFIX': 'daffy_cache', 
        'TIMEOUT': 300, 
    } 
} 

SESSION_ENGINE = 'django.contrib.sessions.backends.cache' 
SESSION_CACHE_ALIAS = 'default' 


# REST Framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(days=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
}

# CORS
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True

# Static & Media
STATIC_URL = '/static/'
STATICFILES_DIRS = [os.path.join(BASE_DIR, '../frontend')]
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Custom User Model
AUTH_USER_MODEL = 'accounts.User'

# WebRTC Settings
TURN_SERVERS = [
    {
        'urls': ['stun:stun.l.google.com:19302'],
    },
    {
        'urls': ['turn:openrelay.metered.ca:80'],
        'username': 'openrelayproject',
        'credential': 'openrelayproject',
    },
]

# Redis Settings
REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = os.getenv('REDIS_PORT', '6379')
REDIS_DB = os.getenv('REDIS_DB', '0')

# Celery Configuration
CELERY_BROKER_URL = f'redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}'
CELERY_RESULT_BACKEND = f'redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}'

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
}

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'