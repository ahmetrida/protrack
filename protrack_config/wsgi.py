# Force Launch - ProTrack v1.07 Enterprise Edition
import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'protrack_config.settings')
application = get_wsgi_application()
