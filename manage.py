#!/usr/bin/env python
"""
Proxy manage.py in repository root to allow running `python manage.py` directly.
Forwards execution to backend/manage.py.
"""
import os
import sys
from pathlib import Path

if __name__ == '__main__':
    backend_dir = Path(__file__).resolve().parent / 'backend'
    os.chdir(backend_dir)
    sys.path.insert(0, str(backend_dir))
    
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.dev_settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)
