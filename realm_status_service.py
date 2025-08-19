#!/usr/bin/env python3
"""
Realm Status Service - Fetches and stores status data from Realm canisters
"""
import json
import logging
import os
import subprocess
import time
from typing import Dict, List, Optional
from database.db_client import DatabaseClient

logger = logging.getLogger(__name__)

class RealmStatusService:
    def __init__(self, db_client: DatabaseClient = None):
        self.db_client = db_client or DatabaseClient()
        
    def fetch_realm_status_via_dfx(self, realm_principal: str, realm_url: str = None, network: str = 'ic') -> Optional[Dict]:
        """
        Fetch realm status using DFX canister call with JSON output
        
        Args:
            realm_principal: The principal ID of the realm canister
            realm_url: Optional URL (not used for DFX calls but kept for compatibility)
            network: Network to use for DFX call (default: 'ic')
        
        Returns:
            Dict containing the realm status data, or None if failed
        """
        try:
            logger.info(f"Fetching realm status via DFX for {realm_principal} on network {network}")
            
            # Set environment variables for DFX security warnings
            env = os.environ.copy()
            if network == 'ic':
                # Suppress mainnet plaintext identity warning for read-only operations
                env['DFX_WARNING'] = '-mainnet_plaintext_identity'
            
            # Run DFX canister call command with JSON output
            cmd = [
                'dfx', 'canister', 'call',
                '--network', network,
                '--output', 'json',
                realm_principal,
                'status'
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                env=env
            )
            
            if result.returncode != 0:
                logger.error(f"DFX call failed for {realm_principal}: {result.stderr}")
                return None
            
            # Parse the JSON response directly
            try:
                response_data = json.loads(result.stdout)
                logger.info(f"Successfully fetched realm status via DFX for {realm_principal}")
                return response_data
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON response from {realm_principal}: {e}")
                logger.debug(f"Raw DFX output: {result.stdout}")
                return None
            
        except subprocess.TimeoutExpired:
            logger.error(f"DFX call timed out for realm {realm_principal}")
            return None
        except Exception as e:
            logger.error(f"Error fetching realm status via DFX for {realm_principal}: {e}")
            return None
    
    
    
    def fetch_and_store_realm_status(self, realm_principal: str, realm_url: str = None, network: str = "ic") -> bool:
        """Fetch realm status and store it in the database"""
        try:
            logger.info(f"Fetching and storing status for realm: {realm_principal}")
            
            # Use DFX to fetch status data
            status_data = self.fetch_realm_status_via_dfx(realm_principal, realm_url, network)
            
            if not status_data:
                logger.error(f"Failed to fetch status data for realm {realm_principal}")
                return False
            
            # Use realm_url if provided, otherwise construct from principal
            if not realm_url:
                realm_url = f"https://{realm_principal}.ic0.app"
            
            # Store in database
            status_id = self.db_client.store_realm_status(realm_principal, realm_url, status_data)
            logger.info(f"Successfully stored realm status with ID: {status_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error fetching and storing realm status: {e}")
            return False
    
    def fetch_multiple_realms_status(self, realms: List[Dict[str, str]], network: str = "ic") -> Dict[str, bool]:
        """Fetch status for multiple realms using DFX"""
        results = {}
        
        for realm in realms:
            realm_principal = realm.get('principal')
            realm_url = realm.get('url')
            
            if not realm_principal:
                logger.warning(f"Invalid realm configuration - missing principal: {realm}")
                results[realm_principal or 'unknown'] = False
                continue
            
            success = self.fetch_and_store_realm_status(realm_principal, realm_url, network)
            results[realm_principal] = success
            
            # Add small delay between requests to be respectful
            time.sleep(1)
        
        return results
    
    def get_realm_status_summary(self, realm_principal: str) -> Optional[Dict]:
        """Get a summary of the latest realm status"""
        try:
            latest_status = self.db_client.get_latest_realm_status(realm_principal)
            if not latest_status:
                return None
            
            status_data = latest_status['status_data']
            
            # Create a summary with key metrics
            summary = {
                'realm_principal': latest_status['realm_principal'],
                'realm_url': latest_status['realm_url'],
                'last_updated': latest_status['created_at'].isoformat() if latest_status['created_at'] else None,
                'status_data': status_data,
                'health_score': self._calculate_health_score(status_data)
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"Error getting realm status summary: {e}")
            return None
    
    def _calculate_health_score(self, status_data: Dict) -> float:
        """Calculate a simple health score based on status data"""
        try:
            score = 0.0
            
            # Base score for being online
            if status_data.get('status') == 'ok':
                score += 50.0
            
            # Points for having users
            if status_data.get('users_count', 0) > 0:
                score += 20.0
            
            # Points for having organizations
            if status_data.get('organizations_count', 0) > 0:
                score += 10.0
            
            # Points for having extensions
            extensions = status_data.get('extensions', [])
            if extensions and len(extensions) > 0:
                score += 10.0
            
            # Points for recent activity (having any entities)
            total_entities = (
                status_data.get('mandates_count', 0) + status_data.get('tasks_count', 0) +
                status_data.get('transfers_count', 0) + status_data.get('proposals_count', 0) +
                status_data.get('votes_count', 0)
            )
            if total_entities > 0:
                score += 10.0
            
            return min(score, 100.0)  # Cap at 100
            
        except Exception as e:
            logger.error(f"Error calculating health score: {e}")
            return 0.0
    
    def get_all_realms_summary(self) -> List[Dict]:
        """Get summary for all tracked realms"""
        try:
            all_statuses = self.db_client.get_all_realms_latest_status()
            summaries = []
            
            for status in all_statuses:
                status_data = status['status_data']
                summary = {
                    'realm_principal': status['realm_principal'],
                    'realm_url': status['realm_url'],
                    'last_updated': status['created_at'].isoformat() if status['created_at'] else None,
                    'status_data': status_data,
                    'health_score': self._calculate_health_score(status_data)
                }
                summaries.append(summary)
            
            # Sort by health score descending
            summaries.sort(key=lambda x: x['health_score'], reverse=True)
            return summaries
            
        except Exception as e:
            logger.error(f"Error getting all realms summary: {e}")
            return []
