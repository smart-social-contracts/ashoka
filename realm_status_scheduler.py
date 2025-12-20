#!/usr/bin/env python3
"""
Realm Status Scheduler - Background service for periodic realm status fetching
"""
import json
import logging
import os
import threading
import time
from typing import Dict, List
from realm_status_service import RealmStatusService
from database.db_client import DatabaseClient

logger = logging.getLogger(__name__)

class RealmStatusScheduler:
    def __init__(self, db_client: DatabaseClient = None):
        self.db_client = db_client or DatabaseClient()
        self.realm_status_service = RealmStatusService(self.db_client)
        self.scheduler_thread = None
        self.running = False
        self.realms_config = []
        
        # Configuration from environment variables
        self.fetch_interval = int(os.getenv('REALM_STATUS_FETCH_INTERVAL', '300'))  # 5 minutes default
        self.enabled = os.getenv('REALM_STATUS_SCHEDULER_ENABLED', 'false').lower() == 'true'
        self.network = os.getenv('REALM_STATUS_NETWORK', 'ic')  # Default to IC mainnet
        
        # Load realms configuration
        self.load_realms_config()
    
    def load_realms_config(self):
        """Load realms configuration from environment or config file"""
        try:
            # Try to load from environment variable first
            realms_json = os.getenv('REALMS_CONFIG')
            if realms_json:
                self.realms_config = json.loads(realms_json)
                logger.info(f"Loaded {len(self.realms_config)} realms from environment")
                return
            
            # Try to load from config file
            config_file = os.path.join(os.path.dirname(__file__), 'realms_config.json')
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    self.realms_config = json.load(f)
                logger.info(f"Loaded {len(self.realms_config)} realms from config file")
                return
            
            # Default configuration for development
            self.realms_config = [
                {
                    "principal": "rdmx6-jaaaa-aaaah-qcaiq-cai",
                    "url": "https://rdmx6-jaaaa-aaaah-qcaiq-cai.ic0.app",
                    "name": "Demo Realm"
                }
            ]
            logger.info("Using default realms configuration")
            
        except Exception as e:
            logger.error(f"Error loading realms configuration: {e}")
            traceback.print_exc()
            self.realms_config = []
    
    def start(self):
        """Start the background scheduler"""
        if not self.enabled:
            logger.info("Realm status scheduler is disabled")
            return
        
        if self.running:
            logger.warning("Scheduler is already running")
            return
        
        if not self.realms_config:
            logger.warning("No realms configured, scheduler will not start")
            return
        
        self.running = True
        self.scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self.scheduler_thread.start()
        logger.info(f"Started realm status scheduler with {len(self.realms_config)} realms, interval: {self.fetch_interval}s")
    
    def stop(self):
        """Stop the background scheduler"""
        if self.running:
            self.running = False
            logger.info("Stopped realm status scheduler")
    
    def _scheduler_loop(self):
        """Main scheduler loop"""
        while self.running:
            try:
                logger.info("Starting scheduled realm status fetch")
                start_time = time.time()
                
                # Fetch status for all configured realms using DFX
                results = self.realm_status_service.fetch_multiple_realms_status(self.realms_config, self.network)
                
                # Log results
                successful = sum(1 for success in results.values() if success)
                total = len(results)
                elapsed = time.time() - start_time
                
                logger.info(f"Scheduled fetch completed: {successful}/{total} successful in {elapsed:.2f}s")
                
                # Log any failures
                for realm_principal, success in results.items():
                    if not success:
                        logger.warning(f"Failed to fetch status for realm: {realm_principal}")
                
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                traceback.print_exc()
            
            # Wait for next interval
            time.sleep(self.fetch_interval)
    
    def fetch_now(self) -> Dict[str, bool]:
        """Trigger an immediate fetch for all configured realms using DFX"""
        try:
            logger.info("Triggering immediate realm status fetch via DFX")
            results = self.realm_status_service.fetch_multiple_realms_status(self.realms_config, self.network)
            
            successful = sum(1 for success in results.values() if success)
            total = len(results)
            logger.info(f"Immediate fetch completed: {successful}/{total} successful")
            
            return results
            
        except Exception as e:
            logger.error(f"Error in immediate fetch: {e}")
            traceback.print_exc()
            return {}
    
    def add_realm(self, realm_principal: str, realm_url: str, name: str = None):
        """Add a new realm to the configuration"""
        realm_config = {
            "principal": realm_principal,
            "url": realm_url,
            "name": name or f"Realm {realm_principal[:8]}..."
        }
        
        # Check if realm already exists
        for existing in self.realms_config:
            if existing["principal"] == realm_principal:
                logger.warning(f"Realm {realm_principal} already exists in configuration")
                return False
        
        self.realms_config.append(realm_config)
        logger.info(f"Added realm {realm_principal} to configuration")
        
        # Save updated configuration
        self.save_realms_config()
        return True
    
    def remove_realm(self, realm_principal: str):
        """Remove a realm from the configuration"""
        original_count = len(self.realms_config)
        self.realms_config = [r for r in self.realms_config if r["principal"] != realm_principal]
        
        if len(self.realms_config) < original_count:
            logger.info(f"Removed realm {realm_principal} from configuration")
            self.save_realms_config()
            return True
        else:
            logger.warning(f"Realm {realm_principal} not found in configuration")
            return False
    
    def save_realms_config(self):
        """Save the current realms configuration to file"""
        try:
            config_file = os.path.join(os.path.dirname(__file__), 'realms_config.json')
            with open(config_file, 'w') as f:
                json.dump(self.realms_config, f, indent=2)
            logger.info("Saved realms configuration to file")
        except Exception as e:
            logger.error(f"Error saving realms configuration: {e}")
            traceback.print_exc()
    
    def get_status(self) -> Dict:
        """Get scheduler status information"""
        return {
            "enabled": self.enabled,
            "running": self.running,
            "fetch_interval": self.fetch_interval,
            "network": self.network,
            "realms_count": len(self.realms_config),
            "realms": self.realms_config
        }

# Global scheduler instance
_scheduler_instance = None

def get_scheduler() -> RealmStatusScheduler:
    """Get the global scheduler instance"""
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = RealmStatusScheduler()
    return _scheduler_instance

def start_scheduler():
    """Start the global scheduler"""
    scheduler = get_scheduler()
    scheduler.start()

def stop_scheduler():
    """Stop the global scheduler"""
    scheduler = get_scheduler()
    scheduler.stop()
