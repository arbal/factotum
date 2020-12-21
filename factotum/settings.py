import os

from django.contrib.messages import constants as messages

from factotum.environment import env

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DEBUG = env.DEBUG
SECRET_KEY = env.SECRET_KEY
ALLOWED_HOSTS = env.ALLOWED_HOSTS

# IPs allowed to see django-debug-toolbar output
INTERNAL_IPS = ("127.0.0.1",)

FILE_UPLOAD_MAX_MEMORY_SIZE = int(env.MAX_UPLOAD_SIZE)
DATA_UPLOAD_MAX_MEMORY_SIZE = int(env.MAX_UPLOAD_SIZE)
DATA_UPLOAD_MAX_NUMBER_FIELDS = int(env.DATA_UPLOAD_MAX_NUMBER_FIELDS) or None

IS_WS_API = True if env.ROOT_URLCONF == "api" else False

INSTALLED_APPS = [
    "dal",
    "dal_select2",
    "django.contrib.contenttypes",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "bootstrap_datepicker_plus",
    "widget_tweaks",
    "django.contrib.humanize",
    "factotum",
    "debug_toolbar",
    "taggit",
    "taggit_labels",
    "django_extensions",
    "elastic.apps.ElasticConfig",
    "bulkformsets.apps.BulkFormSetsConfig",
    "docs",
    "dashboard.apps.DashboardConfig",
    "feedback.apps.FeedbackConfig",
    "celery_usertask",
    "celery_filetask",
    "celery_formtask",
    "celery_djangotest",
    "celery_resultsview",
    "django_filters",
    "django_prometheus",
    "rest_framework",
    "rest_framework.authtoken",
    "django_mysql",
    "apps_api.api",
    "apps_api.openapi.apps.OpenAPIConfig",
    "apps_api.core",
    "django_elasticsearch_dsl",
    "django_cleanup.apps.CleanupConfig",
    "django_db_views",
]

MIDDLEWARE = [
    # enclose other middlewares between prometheus before/after middleware
    "django_prometheus.middleware.PrometheusBeforeMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "debug_toolbar.middleware.DebugToolbarMiddleware",
    "crum.CurrentRequestUserMiddleware",
    "django_prometheus.middleware.PrometheusAfterMiddleware",
]

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

ROOT_URLCONF = "factotum.urls." + env.ROOT_URLCONF

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [os.path.join(BASE_DIR, "templates")],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "django.template.context_processors.media",
                "factotum.context_processors.settings",
            ]
        },
    }
]

DATABASES = {
    "default": {
        "ENGINE": "factotum.db",
        "NAME": env.SQL_DATABASE,
        "USER": env.SQL_USER,
        "PASSWORD": env.SQL_PASSWORD,
        "HOST": env.SQL_HOST,
        "PORT": env.SQL_PORT,
    }
}
if env.QUERY_LOG_DATABASE != env.SQL_DATABASE:
    DATABASES["querylogdb"] = {
        "ENGINE": "django.db.backends.mysql",
        "NAME": env.QUERY_LOG_DATABASE,
        "USER": env.SQL_USER,
        "PASSWORD": env.SQL_PASSWORD,
        "HOST": env.SQL_HOST,
        "PORT": env.SQL_PORT,
    }
DATABASE_ROUTERS = ["factotum.routers.QueryLogRouter"]

ELASTICSEARCH = {
    "default": {
        "HOSTS": [env.ELASTICSEARCH_HOST + ":" + env.ELASTICSEARCH_PORT],
        "INDEX": "dashboard",
        "HTTP_AUTH": (env.FACTOTUM_ELASTIC_USERNAME, env.FACTOTUM_ELASTIC_PASSWORD),
    }
}

ELASTICSEARCH_DSL = {
    "default": {
        "hosts": [env.ELASTICSEARCH_HOST + ":" + env.ELASTICSEARCH_PORT],
        "http_auth": (env.FACTOTUM_ELASTIC_USERNAME, env.FACTOTUM_ELASTIC_PASSWORD),
    }
}

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": f"redis://{env.REDIS_HOST}:{env.REDIS_PORT}/{env.REDIS_CACHE_DATABASE}",
        "OPTIONS": {"CLIENT_CLASS": "django_redis.client.DefaultClient"},
    }
}
SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_CACHE_ALIAS = "default"

LANGUAGE_CODE = "en-us"
TIME_ZONE = "America/New_York"
USE_I18N = True
USE_L10N = True
USE_TZ = False

STATIC_URL = "/static/"
STATIC_ROOT = os.path.join(BASE_DIR, "collected_static")
STATICFILES_DIRS = [os.path.join(BASE_DIR, "static")]

MEDIA_URL = env.MEDIA_URL
MEDIA_ROOT = env.MEDIA_ROOT

LOGIN_REDIRECT_URL = "index"
LOGIN_URL = "login"

TAGGIT_CASE_INSENSITIVE = True

MESSAGE_TAGS = {
    messages.DEBUG: "alert-info",
    messages.INFO: "alert-info",
    messages.SUCCESS: "alert-success",
    messages.WARNING: "alert-warning",
    messages.ERROR: "alert-danger",
}

DOCS_ROOT = os.path.join(BASE_DIR, "docs/_build/html")

EXTRA = 1

TEST_BROWSER = "chrome"
CHROMEDRIVER_PATH = env.CHROMEDRIVER_PATH

CELERY_BROKER_URL = (
    f"redis://{env.REDIS_HOST}:{env.REDIS_PORT}/{env.REDIS_CELERY_DATABASE}"
)
CELERY_RESULT_BACKEND = CELERY_BROKER_URL
CELERY_FILETASK_ROOT = os.path.join(BASE_DIR, "celeryfiles")

PROMETHEUS_EXPORT_MIGRATIONS = False

LOGGING = {
    "version": 1,
    "filters": {"test_filter": {"()": "factotum.logging.TestFilter"}},
    "formatters": {
        "console": {
            "format": "%(asctime)s [%(levelname)s] %(message)s",
            "datefmt": "[%d/%b/%Y %H:%M:%S]",
            "class": "logging.Formatter",
        },
        "django.server": {
            "()": "django.utils.log.ServerFormatter",
            "format": "[{server_time}] [INFO] {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "level": "INFO",
            "class": "logging.StreamHandler",
            "formatter": "console",
            "filters": ["test_filter"],
        },
        "django.server": {
            "level": "INFO",
            "class": "logging.StreamHandler",
            "formatter": "django.server",
        },
        "logstash": {
            "level": "INFO",
            "class": "logstash.UDPLogstashHandler",
            "host": env.LOGSTASH_HOST,
            "port": int(env.LOGSTASH_PORT),
            "version": 1,
            "message_type": "django",
            "fqdn": False,
            "tags": ["factotum_ws", "access"],
        },
    },
    "loggers": {
        "django": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "django.server": {
            "handlers": ["logstash", "django.server"]
            if IS_WS_API
            else ["django.server"],
            "level": "INFO",
            "propagate": False,
        },
        "gunicorn.access": {
            "level": "INFO",
            "handlers": ["logstash", "console"] if IS_WS_API else ["console"],
            "propagate": False,
        },
        "gunicorn.error": {
            "level": "INFO",
            "handlers": ["console"],
            "propagate": False,
        },
    },
}

DJANGO_EXTENSIONS_RESET_DB_MYSQL_ENGINES = ("factotum.db",)

JSON_API_FORMAT_TYPES = "camelize"
# JSON_API_FORMAT_FIELD_NAMES = "camelize"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "apps_api.core.authentication.ExpiringTokenAuthentication"
    ],
    "EXCEPTION_HANDLER": "rest_framework_json_api.exceptions.exception_handler",
    # "DEFAULT_PAGINATION_CLASS": "rest_framework_json_api.pagination.JsonApiPageNumberPagination",
    "DEFAULT_PAGINATION_CLASS": "apps_api.core.pagination.CustomJsonApiPageNumberPagination",
    "PAGE_SIZE": 100,
    "DEFAULT_PARSER_CLASSES": (
        "rest_framework_json_api.parsers.JSONParser",
        "rest_framework.parsers.FormParser",
        "rest_framework.parsers.MultiPartParser",
    ),
    "DEFAULT_RENDERER_CLASSES": (
        "apps_api.core.jsonapi_fixes.JSONRenderer",
        # If you're performance testing, you will want to use the browseable API
        # without forms, as the forms can generate their own queries.
        # If performance testing, enable:
        # 'example.utils.BrowsableAPIRendererWithoutForms',
        # Otherwise, to play around with the browseable API, enable:
        "rest_framework.renderers.BrowsableAPIRenderer",
    ),
    "DEFAULT_METADATA_CLASS": "rest_framework_json_api.metadata.JSONAPIMetadata",
    "DEFAULT_FILTER_BACKENDS": (
        "rest_framework_json_api.filters.QueryParameterValidationFilter",
        "rest_framework_json_api.filters.OrderingFilter",
        "rest_framework_json_api.django_filters.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
    ),
    "SEARCH_PARAM": "filter[search]",
    "TEST_REQUEST_RENDERER_CLASSES": (
        "apps_api.core.jsonapi_fixes.JSONRenderer",
        "rest_framework.renderers.MultiPartRenderer",
    ),
    "TEST_REQUEST_DEFAULT_FORMAT": "vnd.api+json",
}

SWAGGER_SETTINGS = {
    "DEFAULT_GENERATOR_CLASS": "apps_api.core.generators.StandardSchemaGenerator",
    "DEFAULT_AUTO_SCHEMA_CLASS": "apps_api.core.inspectors.StandardAutoSchema",
    "DEFAULT_FIELD_INSPECTORS": [
        "drf_yasg.inspectors.CamelCaseJSONFilter",
        "drf_yasg.inspectors.ReferencingSerializerInspector",
        "drf_yasg.inspectors.RelatedFieldInspector",
        "drf_yasg.inspectors.ChoiceFieldInspector",
        "drf_yasg.inspectors.FileFieldInspector",
        "drf_yasg.inspectors.DictFieldInspector",
        "drf_yasg.inspectors.JSONFieldInspector",
        "drf_yasg.inspectors.HiddenFieldInspector",
        "drf_yasg.inspectors.RecursiveFieldInspector",
        "drf_yasg.inspectors.SerializerMethodFieldInspector",
        "drf_yasg.inspectors.SimpleFieldInspector",
        "drf_yasg.inspectors.StringDefaultFieldInspector",
    ],
    "DEFAULT_FILTER_INSPECTORS": ["apps_api.core.inspectors.DjangoFiltersInspector"],
    "DEFAULT_PAGINATOR_INSPECTORS": [
        "apps_api.core.inspectors.StandardPaginatorInspector"
    ],
    "SECURITY_DEFINITIONS": {},
}

DJANGO_MYSQL_REWRITE_QUERIES = True
SILENCED_SYSTEM_CHECKS = [
    "django_mysql.W001",
    "django_mysql.W002",
    "django_mysql.W003",
    "django_mysql.W004",
]
