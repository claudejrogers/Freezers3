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

if SQLITE3:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',  # Add 'postgresql_psycopg2', 'mysql', 'sqlite3' or 'oracle'.
            'NAME': root('db.sqlite3'),                      # Or path to database file if using sqlite3.
            # 'USER': '',
            # 'PASSWORD': '',
            # 'HOST': '',                      # Set to empty string for localhost.
            # 'PORT': '',                      # Set to empty string for default.
        }
    }
