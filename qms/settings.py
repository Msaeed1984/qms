from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# ================================
# SECURITY
# ================================
SECRET_KEY = "django-insecure-z&9+nl5ql#^d!q8cbp66b!%25j$j55u*@4*+3!+i_hz&72$i1@"
DEBUG = True

# للتطوير على localhost فقط
ALLOWED_HOSTS = ["127.0.0.1", "localhost"]


# ================================
# APPLICATIONS
# ================================
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # Project apps
    "accounts.apps.AccountsConfig",
    "documents.apps.DocumentsConfig",
    "core.apps.CoreConfig",
]


# ================================
# MIDDLEWARE
# ================================
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",

    # ✅ Needed for iframe viewer
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]


# ================================
# CLICKJACKING / IFRAME POLICY
# ================================
# ✅ Allow embedding ONLY from same origin (required for internal PDF iframe viewer)
X_FRAME_OPTIONS = "SAMEORIGIN"


# ================================
# URLS
# ================================
ROOT_URLCONF = "qms.urls"


# ================================
# TEMPLATES
# ================================
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",

        # Global templates folders
        "DIRS": [
            BASE_DIR / "templates",
            BASE_DIR / "templates" / "qms-templates",
        ],

        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]


# ================================
# WSGI
# ================================
WSGI_APPLICATION = "qms.wsgi.application"


# ================================
# DATABASE
# ================================
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}


# ================================
# PASSWORD VALIDATION
# ================================
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# ================================
# INTERNATIONALIZATION
# ================================
LANGUAGE_CODE = "en-us"

TIME_ZONE = "Asia/Dubai"   # ← هذا المهم

USE_I18N = True
USE_TZ = True

# ================================
# STATIC FILES
# ================================
STATIC_URL = "/static/"

STATICFILES_DIRS = [
    BASE_DIR / "static",
]

STATIC_ROOT = BASE_DIR / "staticfiles"


# ================================
# MEDIA FILES
# ================================
# ✅ MUST start and end properly for file urls
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"


# ================================
# DEFAULT PK
# ================================
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# ================================
# CUSTOM USER MODEL
# ================================
AUTH_USER_MODEL = "accounts.User"


# ================================
# AUTHENTICATION / LOGIN SYSTEM
# ================================
LOGIN_URL = "/login/"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/login/"


# ================================
# SESSION SETTINGS
# ================================
SESSION_COOKIE_AGE = 60 * 60 * 8  # 8 hours
SESSION_SAVE_EVERY_REQUEST = True