import os

# pgAdmin4 configuration for standalone server mode
DEFAULT_USER = 'admin@ashoka.local'
DEFAULT_PASSWORD = 'ashoka_admin_pass'

# Server configuration
SERVER_MODE = False  # Run in desktop mode for simplicity
WTF_CSRF_ENABLED = True

# Data and log directories
DATA_DIR = '/tmp/pgadmin'
LOG_FILE = '/tmp/pgadmin/pgadmin4.log'
SESSION_DB_PATH = '/tmp/pgadmin/sessions'
SQLITE_PATH = '/tmp/pgadmin/pgadmin4.db'

# Security
SECRET_KEY = 'ashoka-pgadmin-secret-key-2024'

# Network configuration
DEFAULT_SERVER = '0.0.0.0'
DEFAULT_SERVER_PORT = 5050

# Allow all hosts in container environment
ALLOWED_HOSTS = ['*']

# Session configuration
SESSION_EXPIRATION_TIME = 86400  # 24 hours

# Disable enhanced cookie protection for container environment
ENHANCED_COOKIE_PROTECTION = False

# Authentication settings
AUTHENTICATION_SOURCES = ['internal']
MASTER_PASSWORD_REQUIRED = False

# Console settings
CONSOLE_LOG_LEVEL = 20  # INFO
FILE_LOG_LEVEL = 20     # INFO