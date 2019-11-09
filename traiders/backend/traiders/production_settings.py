from .settings import *
from django.core.management.utils import get_random_secret_key


# Override development settings
DEBUG = False

ALLOWED_HOSTS = [
    'api.traiders.tk'
]

SECRET_KEY = os.environ.get('SECRET_KEY')

# Use postgres in production
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'HOST': 'db',
        'PORT': '5432',
        'NAME': 'postgres',
        'USER': 'postgres',
        'PASSWORD': 'postgres'
    }
}

STATIC_URL = '/static/'
STATIC_ROOT = '/static/'

MEDIA_ROOT = '/media'
MEDIA_URL = '//media.traiders.tk/'

# make returned urls https
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
