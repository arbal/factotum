import os
from pathlib import Path
import shutil

from dotenv import load_dotenv


class MetaEnv(type):
    prefix = "FACTOTUM_"

    @property
    def DEBUG(cls):
        default = "true"
        return cls._get("DEBUG", default, prefix=True) in cls.truevals

    @property
    def ROOT_URLCONF(cls):
        default = "factotum"
        return cls._get("ROOT_URLCONF", default, prefix=False)

    @property
    def SECRET_KEY(cls):
        default = "factotum" if cls.DEBUG else ""
        return cls._get("SECRET_KEY", default, prefix=True)

    @property
    def ALLOWED_HOSTS(cls):
        default = "*"
        return [
            host
            for host in cls._get("ALLOWED_HOSTS", default, prefix=True).split(",")
            if host
        ]

    @property
    def MAX_UPLOAD_SIZE(cls):
        default = "5242880"
        return cls._get("MAX_UPLOAD_SIZE", default)

    @property
    def DATA_UPLOAD_MAX_NUMBER_FIELDS(cls):
        default = "10000"
        return cls._get("DATA_UPLOAD_MAX_NUMBER_FIELDS", default)

    @property
    def MEDIA_ROOT(cls):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        default = os.path.join(base_dir, "media")
        return cls._get("MEDIA_ROOT", default)

    @property
    def MEDIA_URL(cls):
        default = "/media/"
        return cls._get("MEDIA_URL", default)

    @property
    def DOWNLOADS_ROOT(cls):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        default = os.path.join(base_dir, "downloads")
        return cls._get("DOWNLOADS_ROOT", default)

    @property
    def FACTOTUM_PORT(cls):
        deafult = "8000"
        return cls._get("FACTOTUM_PORT", deafult)

    @property
    def FACTOTUM_WS_PORT(cls):
        default = "8001"
        return cls._get("FACTOTUM_WS_PORT", default)

    @property
    def FACTOTUM_WS_TOKEN_TTL(cls):
        default = 1000 * 60 * 15  # 15 minute lifespan by default
        return int(cls._get("FACTOTUM_WS_TOKEN_TTL", default))

    @property
    def FACTOTUM_WS_VERSION_NUMBER(cls):
        default = "Not Specified"  # 15 minute lifespan by default
        return cls._get("FACTOTUM_WS_VERSION_NUMBER", default)

    @property
    def SQL_DATABASE(cls):
        default = "factotum" if cls.DEBUG else ""
        return cls._get("SQL_DATABASE", default)

    @property
    def SQL_HOST(cls):
        default = "127.0.0.1" if cls.DEBUG else ""
        sql_host = cls._get("SQL_HOST", default)
        # Force TCP connection rather than UNIX socket
        if sql_host == "localhost":
            return "127.0.0.1"
        return sql_host

    @property
    def SQL_PORT(cls):
        default = "3306"
        return cls._get("SQL_PORT", default)

    @property
    def SQL_USER(cls):
        default = "root" if cls.DEBUG else ""
        return cls._get("SQL_USER", default)

    @property
    def SQL_PASSWORD(cls):
        default = ""
        return cls._get("SQL_PASSWORD", default)

    @property
    def QUERY_LOG_DATABASE(cls):
        default = cls.SQL_DATABASE if cls.DEBUG else ""
        return cls._get("QUERY_LOG_DATABASE", default)

    @property
    def ELASTICSEARCH_HOST(cls):
        default = "localhost"
        return cls._get("ELASTICSEARCH_HOST", default)

    @property
    def ELASTICSEARCH_PORT(cls):
        default = "9200"
        return cls._get("ELASTICSEARCH_PORT", default)

    @property
    def FACTOTUM_ELASTIC_USERNAME(cls):
        default = ""
        return cls._get("FACTOTUM_ELASTIC_USERNAME", default)

    @property
    def FACTOTUM_ELASTIC_PASSWORD(cls):
        default = ""
        return cls._get("FACTOTUM_ELASTIC_PASSWORD", default)

    @property
    def REDIS_CACHE_DATABASE(cls):
        default = "0"
        return cls._get("REDIS_CACHE_DATABASE", default)

    @property
    def REDIS_CELERY_DATABASE(cls):
        default = "1"
        return cls._get("REDIS_CELERY_DATABASE", default)

    @property
    def REDIS_CACHEOPS_DATABASE(cls):
        default = "2"
        return cls._get("REDIS_CACHEOPS_DATABASE", default)

    @property
    def REDIS_HOST(cls):
        default = "localhost"
        return cls._get("REDIS_HOST", default)

    @property
    def REDIS_PORT(cls):
        default = "6379"
        return cls._get("REDIS_PORT", default)

    @property
    def REDIS_PASSWORD(cls):
        default = "factotum"
        return cls._get("REDIS_PASSWORD", default)

    @property
    def CACHEOPS_DEFAULT_TIMEOUT(cls):
        default = 60 * 60  # default to one hour
        return int(cls._get("CACHEOPS_DEFAULT_TIMEOUT", default))

    @property
    def CHROMEDRIVER_PATH(cls):
        chromedriver_in_path = shutil.which("chromedriver")
        if chromedriver_in_path:
            default = chromedriver_in_path
        else:
            default = ""
        return cls._get("CHROMEDRIVER_PATH", default)

    @property
    def GUNICORN_OPTS(cls):
        default = ""
        return {
            k: v
            for entry in cls._get("GUNICORN_OPTS", default, prefix=True).split(",")
            if entry
            for k, v in entry.split("=")
        }

    @property
    def ENABLE_GOOGLE_ANALYTICS(cls):
        default = False
        return (
            cls._get("ENABLE_GOOGLE_ANALYTICS", default, prefix=False) in cls.truevals
        )

    @property
    def PRODUCT_IMAGE_DIRECTORY_MAX_UPLOAD(cls):
        default = 5000000
        return int(
            cls._get("PRODUCT_IMAGE_DIRECTORY_MAX_UPLOAD", default, prefix=False)
        )

    @property
    def PRODUCT_IMAGE_DIRECTORY_MAX_FILE_COUNT(cls):
        default = 500
        return int(
            cls._get("PRODUCT_IMAGE_DIRECTORY_MAX_FILE_COUNT", default, prefix=False)
        )

    @property
    def PRODUCT_IMAGE_MAX_SIZE(cls):
        default = 1000000
        return int(cls._get("PRODUCT_IMAGE_MAX_SIZE", default, prefix=False))

    @property
    def PROVISIONAL_ASSIGNMENT_SCHEDULE(cls):
        default = "0 3 * * *"
        return cls._get("PROVISIONAL_ASSIGNMENT_SCHEDULE", default, prefix=False)

    @property
    def GENERATE_BULK_DOWNLOAD_SCHEDULE(cls):
        default = "0 4 * * *"
        return cls._get("GENERATE_BULK_DOWNLOAD_SCHEDULE", default, prefix=False)

    @property
    def LOGSTASH_HOST(cls):
        default = "localhost"
        return cls._get("LOGSTASH_HOST", default)

    @property
    def LOGSTASH_PORT(cls):
        default = "5959"
        return cls._get("LOGSTASH_PORT", default)


class env(metaclass=MetaEnv):
    truevals = ("true", "True", "yes", "y", "1", "on", "ok", True)

    def load():
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        base_env = os.path.join(base_dir, ".env")
        load_dotenv(dotenv_path=Path(base_env))
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "factotum.settings")

    load()

    @classmethod
    def _get(cls, key, default, prefix=False):
        value = os.getenv(cls.prefix + key)
        global_value = os.getenv(key)
        if value and prefix:
            return value
        elif not global_value:
            return default
        return global_value
