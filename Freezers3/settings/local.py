# Local Django settings

SQLITE3 = False

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

