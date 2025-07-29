import os

# pgAdmin4 local configuration

# Basic settings
DEFAULT_USER = 'admin@ashoka.local'
DEFAULT_PASSWORD = 'ashoka_admin_pass'

# Server configuration
SERVER_MODE = False  # Desktop mode for simplicity
WTF_CSRF_ENABLED = True

# Override directory paths to use accessible locations
DATA_DIR = '/var/lib/pgadmin'
LOG_FILE = '/var/lib/pgadmin/pgadmin4.log'
SESSION_DB_PATH = '/var/lib/pgadmin/sessions'
SQLITE_PATH = '/var/lib/pgadmin/pgadmin4.db'

# Ensure directories exist
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(os.path.dirname(SESSION_DB_PATH), exist_ok=True)

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

# Disable upgrade check
UPGRADE_CHECK_ENABLED = False

# Email settings (disabled)
MAIL_SERVER = None
MAIL_PORT = 587
MAIL_USE_TLS = False
MAIL_USE_SSL = False
MAIL_USERNAME = None
MAIL_PASSWORD = None

# Configure default server connection for Ashoka database
# This will create a pre-configured server entry
SERVERS = {
    1: {
        'Name': 'Ashoka PostgreSQL',
        'Group': 'Servers',
        'Host': 'localhost',
        'Port': 5432,
        'MaintenanceDB': 'ashoka_db',
        'Username': 'ashoka_user',
        'UseSSHTunnel': 0,
        'TunnelHost': '',
        'TunnelPort': '',
        'TunnelUsername': '',
        'TunnelAuthentication': 0
    }
}