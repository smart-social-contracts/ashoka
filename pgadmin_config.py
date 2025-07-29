import os

# pgAdmin4 configuration
MAIL_SERVER = 'localhost'
MAIL_PORT = 587
MAIL_USE_TLS = False
MAIL_USE_SSL = False
MAIL_USERNAME = ''
MAIL_PASSWORD = ''

# Default admin user
DEFAULT_USER = 'admin@ashoka.local'
DEFAULT_PASSWORD = 'ashoka_admin_pass'

# Server configuration
SERVER_MODE = True
WTF_CSRF_ENABLED = True

# Database configuration for pgAdmin4's metadata
SQLITE_PATH = '/var/lib/pgadmin/pgadmin4.db'

# Log configuration
LOG_FILE = '/var/log/pgadmin/pgadmin4.log'
SESSION_DB_PATH = '/var/lib/pgadmin/sessions'

# Security
SECRET_KEY = 'ashoka-pgadmin-secret-key-2024'

# Allow all hosts in container environment
ALLOWED_HOSTS = ['*']

# Data directory
DATA_DIR = '/var/lib/pgadmin'

# Session configuration
SESSION_EXPIRATION_TIME = 86400  # 24 hours

# Configure default server connection
SERVERS = {
    'localhost': {
        'Name': 'Ashoka PostgreSQL',
        'Group': 'Servers',
        'Host': 'localhost',
        'Port': 5432,
        'MaintenanceDB': 'ashoka_db',
        'Username': 'ashoka_user',
        'SSLMode': 'prefer',
        'SSLCert': '',
        'SSLKey': '',
        'SSLRootCert': '',
        'SSLCrl': '',
        'SSLCompression': 0,
        'Timeout': 10,
        'UseSSHTunnel': 0,
        'TunnelHost': '',
        'TunnelPort': 22,
        'TunnelUsername': '',
        'TunnelAuthentication': 0
    }
}