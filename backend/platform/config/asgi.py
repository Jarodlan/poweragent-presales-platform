import os
from django.core.asgi import get_asgi_application

from config.env import load_env_file

load_env_file()
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

application = get_asgi_application()
