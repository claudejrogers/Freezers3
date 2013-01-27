# Local Django settings

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'freezers',                      # Or path to database file if using sqlite3.
        'USER': 'cjrogers',
        # 'PASSWORD': '',
        # 'HOST': '',                      # Set to empty string for localhost.
        # 'PORT': '',                      # Set to empty string for default.
    }
}

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://media.lawrence.com/media/", "http://example.com/media/"
MEDIA_URL = 'http://127.0.0.1:8000/resources/'

# URL prefix for static files.
# Example: "http://media.lawrence.com/static/"
STATIC_URL = 'http://127.0.0.1:8000/static/'
