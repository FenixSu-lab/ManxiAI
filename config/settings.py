"""
Django settings for ManxiAI project.
"""
import os
import warnings
from pathlib import Path
from dotenv import load_dotenv

warnings.filterwarnings(
    'ignore',
    message='pkg_resources is deprecated as an API.*',
    category=UserWarning,
)

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables
load_dotenv(BASE_DIR / '.env')


def getenv_str(name: str, default: str = '') -> str:
    """Return a stripped environment variable value with empty-string fallback."""
    value = os.getenv(name)
    if value is None:
        return default
    value = value.strip()
    return value if value else default


def getenv_int(name: str, default: int) -> int:
    """Return an integer environment variable value with safe fallback."""
    value = getenv_str(name, str(default))
    try:
        return int(value)
    except ValueError:
        return default

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-manxiai-development-key-change-in-production')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv('DEBUG', 'True').lower() == 'true'

ALLOWED_HOSTS = [host.strip() for host in os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',') if host.strip()]

CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in getenv_str(
        'CSRF_TRUSTED_ORIGINS',
        'http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173,http://127.0.0.1:5173',
    ).split(',')
    if origin.strip()
]

# Application definition
DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

THIRD_PARTY_APPS = [
    'rest_framework',
    'rest_framework.authtoken',
    'corsheaders',
    'django_filters',
    'drf_yasg',
    'django_extensions',
]

LOCAL_APPS = [
    'apps.core',
    'apps.users',
    'apps.knowledge_base',
    'apps.document',
    'apps.chat',
    'apps.embedding',
    'apps.pipeline',
    'apps.workflow',
    'apps.model_management',
    'apps.mcp_server',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
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

WSGI_APPLICATION = 'config.wsgi.application'

# Database
USE_SQLITE = getenv_str('USE_SQLITE', 'False').lower() == 'true'

if USE_SQLITE:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
else:
    DB_CONNECT_TIMEOUT = getenv_int('DB_CONNECT_TIMEOUT', 10)
    DB_SSLMODE = getenv_str('DB_SSLMODE', 'disable')
    DB_GSSENCMODE = getenv_str('DB_GSSENCMODE', 'disable')
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': getenv_str('DB_NAME', 'manxiai'),
            'USER': getenv_str('DB_USER', 'postgres'),
            'PASSWORD': getenv_str('DB_PASSWORD', ''),
            'HOST': getenv_str('DB_HOST', '127.0.0.1'),
            'PORT': getenv_str('DB_PORT', '5432'),
            'CONN_MAX_AGE': getenv_int('DB_CONN_MAX_AGE', 60),
            'CONN_HEALTH_CHECKS': True,
            'OPTIONS': {
                'connect_timeout': DB_CONNECT_TIMEOUT,
                'sslmode': DB_SSLMODE,
                'gssencmode': DB_GSSENCMODE,
                'application_name': getenv_str('DB_APPLICATION_NAME', 'manxiai-django'),
            },
        }
    }

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'zh-hans'
TIME_ZONE = 'Asia/Shanghai'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Custom User Model
AUTH_USER_MODEL = 'users.User'

# REST Framework configuration
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
}

# CORS settings
CORS_ALLOW_ALL_ORIGINS = DEBUG
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

# Hosted MCP Server public base URL, for example: http://192.168.1.14:8000
MCP_PUBLIC_BASE_URL = getenv_str('MCP_PUBLIC_BASE_URL', '')
MCP_ALLOWED_ORIGINS = getenv_str('MCP_ALLOWED_ORIGINS', '')

# Swagger/OpenAPI settings
SWAGGER_SETTINGS = {
    'SECURITY_DEFINITIONS': {
        'Token': {
            'type': 'apiKey',
            'name': 'Authorization',
            'in': 'header'
        }
    }
}

# Celery Configuration
CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE

# AI Model Configuration
DEEPSEEK_API_KEY = getenv_str('DEEPSEEK_API_KEY', '')
DEEPSEEK_BASE_URL = getenv_str('DEEPSEEK_BASE_URL', 'https://api.deepseek.com')

# 保持OpenAI作为备选
OPENAI_API_KEY = getenv_str('OPENAI_API_KEY', '')
OPENAI_BASE_URL = getenv_str('OPENAI_BASE_URL', 'https://api.openai.com/v1')

# 默认使用DeepSeek
DEFAULT_LLM_PROVIDER = getenv_str('DEFAULT_LLM_PROVIDER', 'deepseek')
DEFAULT_LLM_MODEL = getenv_str('DEFAULT_LLM_MODEL', 'deepseek-chat')

# Embedding configuration
EMBEDDING_PROVIDER = getenv_str('EMBEDDING_PROVIDER', 'http_openai_compatible')
EMBEDDING_MODEL = getenv_str('EMBEDDING_MODEL', 'bge-large-zh-v1.5')
EMBEDDING_DIMENSIONS = int(os.getenv('EMBEDDING_DIMENSIONS', '1024'))
EMBEDDING_API_URL = getenv_str('EMBEDDING_API_URL', '')
EMBEDDING_API_KEY = getenv_str('EMBEDDING_API_KEY', '')
EMBEDDING_REQUEST_TIMEOUT = int(os.getenv('EMBEDDING_REQUEST_TIMEOUT', '60'))
EMBEDDING_BATCH_SIZE = int(os.getenv('EMBEDDING_BATCH_SIZE', '16'))
RUN_BACKGROUND_TASKS_SYNC = getenv_str('RUN_BACKGROUND_TASKS_SYNC', 'False').lower() == 'true'

# Vector Database Configuration
VECTOR_DATABASE = {
    'ENGINE': 'pgvector',
    'TABLE_NAME': 'embeddings',
    'SIMILARITY_THRESHOLD': float(getenv_str('SIMILARITY_THRESHOLD', '0.7')),
    'TOP_K': int(getenv_str('TOP_K', '5')),
}

# File Upload Configuration
FILE_UPLOAD_MAX_MEMORY_SIZE = 50 * 1024 * 1024  # 50MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 50 * 1024 * 1024  # 50MB

# Logging Configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file': {
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'django.log',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': getenv_str('DJANGO_LOG_LEVEL', 'INFO'),
            'propagate': True,
        },
        'manxiai': {
            'handlers': ['console', 'file'],
            'level': getenv_str('MANXIAI_LOG_LEVEL', 'INFO'),
            'propagate': True,
        },
    },
} 
