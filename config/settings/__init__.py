"""
Django settings loader based on environment
"""
import os
from pathlib import Path
from decouple import config, Csv

BASE_DIR = Path(__file__).resolve().parent.parent.parent


env = config('DJANGO_ENV', 'development')
print(f"env {env}")

if env == 'production':
    from .production import *
elif env == 'testing':
    from .testing import *
else:
    from .development import *
