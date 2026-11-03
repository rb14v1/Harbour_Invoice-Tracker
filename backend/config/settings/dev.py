from decouple import Csv, config

from .base import *  # noqa: F401,F403

DEBUG = config("DJANGO_DEBUG", cast=bool)
ALLOWED_HOSTS = config("DJANGO_ALLOWED_HOSTS", cast=Csv())
