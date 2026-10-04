import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ['DJANGO_SECRET_KEY']

DEBUG = os.environ['DJANGO_DEBUG'] == 'True'

ALLOWED_HOSTS = os.environ['DJANGO_ALLOWED_HOSTS'].split(',')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.humanize',
    'django.contrib.staticfiles',
    # Third-party
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
    'drf_spectacular',
    # Local apps
    'accounts',
    'portal_config',
    'ict_requisition',
    'transport_requisition',
    'internal_requisition',
    'notifications',
    'contracts',
    'employees',
    'payslip',
    'meetspace',
    'api',
    'django_q',
]

AUTH_USER_MODEL = 'accounts.User'

# ---------------------------------------------------------------------------
# Module feature flags
# ---------------------------------------------------------------------------
# Functional modules that are switched on. To re-enable a module, add its key
# here — no code changes needed. Disabled modules keep their apps installed,
# their tables and their existing data; they are simply unrouted and hidden
# from the UI.
#
#   'ict'       -> ICT requisitions
#   'transport' -> Transport requisitions
#   'internal'  -> Internal requisitions
#   'hr'        -> HR (contracts, employees, payslip)
#
# 'accounts' and 'notifications' are core and always active.
ALL_MODULES = ('ict', 'transport', 'internal', 'hr')
ENABLED_MODULES = ['ict', 'transport', 'internal', 'meetspace', 'hr']

# Modules surfaced in the UI. A module can stay enabled (routed, data intact,
# reachable by staff) while being hidden from the nav, landing page, dashboard
# and "My Requisitions". This is how a module is parked temporarily without
# being switched off entirely.
VISIBLE_MODULES = ['transport']

# Off-site Google Forms surfaced as cards on the public landing page. These live
# outside the portal, so they are shown regardless of VISIBLE_MODULES.
EXTERNAL_FORMS = [
    {
        'key': 'bu_email',
        'title': 'BRAC University Email',
        'description': 'Request a BRAC University email address for staff and students.',
        'url': 'https://docs.google.com/forms/d/e/1FAIpQLSfoS2BCEoAnFxu6DnT00DaAikaCWwuqstZHr7LmIV2Kwqb-nw/viewform',
        'icon': 'bi-envelope-paper',
        'bg': '#EDE9FE',
        'fg': '#6D28D9',
        'cta': 'Open form',
    },
    {
        'key': 'ict_form',
        'title': 'ICT Requisition',
        'description': 'Request IT equipment, software licences and accessories.',
        'url': 'https://docs.google.com/forms/d/e/1FAIpQLScNgf61ZQ-cV3q4CXbsbZuQN0Q_HFI9Y3jCPNaElVJi7KpV5Q/viewform',
        'icon': 'bi-pc-display',
        'bg': '#EFF6FF',
        'fg': '#2563EB',
        'cta': 'Open form',
    },
    {
        'key': 'mail_service',
        'title': 'Mail Service',
        'description': 'BRAC University email with an additional 50 GB of cloud storage '
                       '— for @bracu.ac.bd addresses only.',
        'url': 'https://signup.microsoft.com/signup?skug=Education'
               '&StepsData.Email=sdfsd%40bracu.ac.bd'
               '&sku=314c4481-f395-4525-be8b-2ec4bb1e9d91',
        'icon': 'bi-envelope-at',
        'bg': '#FEF2F2',
        'fg': '#DC2626',
        'cta': 'Sign up',
    },
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',  # Must be before CommonMiddleware
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'requisition_portal.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'requisition_portal.context_processors.portal',
            ],
        },
    },
]

WSGI_APPLICATION = 'requisition_portal.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': os.environ.get('DB_ENGINE', 'django.db.backends.sqlite3'),
        'NAME': os.environ.get('DB_NAME', BASE_DIR / 'db.sqlite3'),
        'USER': os.environ.get('DB_USER', ''),
        'PASSWORD': os.environ.get('DB_PASSWORD', ''),
        'HOST': os.environ.get('DB_HOST', ''),
        'PORT': os.environ.get('DB_PORT', ''),
    }
}

AUTH_PASSWORD_VALIDATORS = []

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'Africa/Nairobi'

USE_I18N = True

USE_TZ = True

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

# Django Q — Background task queue
Q_CLUSTER = {
    'name': 'requisition_portal',
    'workers': 2,
    'timeout': 300,
    'retry': 360,
    'max_attempts': 2,
    'queue_limit': 50,
    'orm': 'default',
}

LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/accounts/login/'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ---------------------------------------------------------------------------
# Django REST Framework
# ---------------------------------------------------------------------------
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_FILTER_BACKENDS': (
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ),
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'EXCEPTION_HANDLER': 'rest_framework.views.exception_handler',
}

# ---------------------------------------------------------------------------
# Simple JWT
# ---------------------------------------------------------------------------
from datetime import timedelta
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'VERIFYING_KEY': None,
    'AUDIENCE': None,
    'ISSUER': None,
    'JWK_URL': None,
    'LEEWAY': 0,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    'USER_AUTHENTICATION_RULE': 'rest_framework_simplejwt.authentication.default_user_authentication_rule',
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_TYPE_CLAIM': 'token_type',
    'TOKEN_USER_CLASS': 'rest_framework_simplejwt.models.TokenUser',
    'JTI_CLAIM': 'jti',
    'SLIDING_TOKEN_REFRESH_EXP_CLAIM': 'refresh_exp',
    'SLIDING_TOKEN_LIFETIME': timedelta(minutes=5),
    'SLIDING_TOKEN_REFRESH_LIFETIME': timedelta(days=1),
}

# ---------------------------------------------------------------------------
# CORS Headers (for React dev server)
# ---------------------------------------------------------------------------
CORS_ALLOWED_ORIGINS = [
    'http://localhost:5173',   # Vite default
    'http://127.0.0.1:5173',
    'http://localhost:3000',   # CRA default
    'http://127.0.0.1:3000',
]
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_ALL_ORIGINS = DEBUG  # Allow all in debug mode

# ---------------------------------------------------------------------------
# DRF Spectacular (OpenAPI/Swagger)
# ---------------------------------------------------------------------------
SPECTACULAR_SETTINGS = {
    'TITLE': 'Requisition Portal API',
    'DESCRIPTION': 'API for BRAC IED Requisition Portal',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'COMPONENT_SPLIT_REQUEST': True,
    'SCHEMA_PATH_PREFIX': '/api/',
    'CONTACT': {'name': 'BRAC IED', 'email': 'support@bracied.org'},
    'LICENSE': {'name': 'Proprietary'},
}
