import logging
import multiprocessing

from factotum.environment import env
from factotum.settings import LOGGING

# Default configuration
# This bind uses the default factotum port for factotum or the webservices port for webservices.
# This should probably be reworked to bind dynamically but currently there is not a foreseeable use-case
bind = ":" + (
    env.FACTOTUM_PORT if env.ROOT_URLCONF == "factotum" else env.FACTOTUM_WS_PORT
)
workers = multiprocessing.cpu_count() * 2 + 1
logconfig_dict = LOGGING
access_log_format = '"%(r)s" %(s)s %(b)s'

# Override/set any configuration variable with environment variables
locals().update(env.GUNICORN_OPTS)


def on_starting(server):
    logger = logging.getLogger("django")
    if env.DEBUG:
        logger.warning("Running in DEBUG mode")
    if "*" in env.ALLOWED_HOSTS:
        logger.warning("Host checking is disabled (ALLOWED_HOSTS is set to accept all)")
