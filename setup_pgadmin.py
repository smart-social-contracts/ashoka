#!/usr/bin/env python3
"""
Setup script for pgAdmin4 initialization
"""
import os
import sys
import subprocess
import json

def setup_pgadmin():
    """Setup pgAdmin4 with default user and server configuration"""
    
    # Create necessary directories
    os.makedirs('/var/lib/pgadmin', exist_ok=True)
    os.makedirs('/var/log/pgadmin', exist_ok=True)
    
    # Set permissions
    os.system('chown -R www-data:www-data /var/lib/pgadmin')
    os.system('chown -R www-data:www-data /var/log/pgadmin')
    os.system('chmod 700 /var/lib/pgadmin')
    
    # Copy configuration file
    config_dir = '/etc/pgadmin'
    os.makedirs(config_dir, exist_ok=True)
    os.system(f'cp /app/ashoka/pgadmin_config.py {config_dir}/config_local.py')
    
    # Setup pgAdmin4 with default user (non-interactive)
    setup_cmd = [
        'python3', '/usr/pgadmin4/web/setup.py',
        '--load-servers', '/app/ashoka/pgadmin_servers.json'
    ]
    
    # Set environment variables for setup
    env = os.environ.copy()
    env['PGADMIN_SETUP_EMAIL'] = 'admin@ashoka.local'
    env['PGADMIN_SETUP_PASSWORD'] = 'ashoka_admin_pass'
    
    try:
        result = subprocess.run(setup_cmd, env=env, capture_output=True, text=True)
        if result.returncode == 0:
            print("pgAdmin4 setup completed successfully")
        else:
            print(f"pgAdmin4 setup failed: {result.stderr}")
            # Try alternative setup method
            setup_alternative()
    except Exception as e:
        print(f"Error during pgAdmin4 setup: {e}")
        setup_alternative()

def setup_alternative():
    """Alternative setup method using direct database creation"""
    print("Trying alternative pgAdmin4 setup...")
    
    # Create the setup script for non-interactive installation
    setup_script = '''
import sys
sys.path.insert(0, '/usr/pgadmin4/web')
from pgadmin import create_app
from pgadmin.model import db, User
from werkzeug.security import generate_password_hash

app = create_app()
with app.app_context():
    db.create_all()
    
    # Check if user already exists
    if not User.query.filter_by(email='admin@ashoka.local').first():
        user = User(
            email='admin@ashoka.local',
            password=generate_password_hash('ashoka_admin_pass'),
            active=True,
            fs_uniquifier='ashoka-admin-unique-id'
        )
        db.session.add(user)
        db.session.commit()
        print("Default admin user created successfully")
    else:
        print("Default admin user already exists")
'''
    
    with open('/tmp/pgadmin_setup.py', 'w') as f:
        f.write(setup_script)
    
    try:
        subprocess.run(['python3', '/tmp/pgadmin_setup.py'], check=True)
        print("Alternative pgAdmin4 setup completed")
    except subprocess.CalledProcessError as e:
        print(f"Alternative setup also failed: {e}")

def create_servers_config():
    """Create the servers configuration file"""
    servers_config = {
        "Servers": {
            "1": {
                "Name": "Ashoka PostgreSQL",
                "Group": "Servers",
                "Host": "localhost",
                "Port": 5432,
                "MaintenanceDB": "ashoka_db",
                "Username": "ashoka_user",
                "SSLMode": "prefer",
                "SSLCert": "",
                "SSLKey": "",
                "SSLRootCert": "",
                "SSLCrl": "",
                "SSLCompression": 0,
                "Timeout": 10,
                "UseSSHTunnel": 0,
                "TunnelHost": "",
                "TunnelPort": 22,
                "TunnelUsername": "",
                "TunnelAuthentication": 0
            }
        }
    }
    
    with open('/app/ashoka/pgadmin_servers.json', 'w') as f:
        json.dump(servers_config, f, indent=2)
    
    print("pgAdmin4 servers configuration created")

if __name__ == "__main__":
    print("Starting pgAdmin4 setup...")
    create_servers_config()
    setup_pgadmin()
    print("pgAdmin4 setup process completed")