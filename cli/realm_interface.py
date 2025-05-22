"""
Realm Interface Module - Handles interactions with GGG-compliant realm canisters
"""

import logging
from typing import Dict, Optional
import ic.client
from ic.identity import Identity
from ic.agent import Agent
from ic.candid import encode, decode

logger = logging.getLogger("ashoka.realm")

class RealmInterface:
    """Interface for interacting with GGG-compliant realm canisters."""
    
    def __init__(self, canister_id: str, network_url: str = "https://ic0.app"):
        """Initialize the realm interface."""
        self.canister_id = canister_id
        self.network_url = network_url
        
        # Initialize IC agent
        identity = Identity()
        self.agent = Agent(identity, network_url)
        logger.info(f"RealmInterface initialized for canister: {canister_id}")
    
    def get_summary(self) -> Optional[str]:
        """Get a summary of the realm via the GGG interface."""
        try:
            logger.info(f"Querying ggg_get_summary from canister {self.canister_id}")
            
            # Call the ggg_get_summary method on the canister
            result = self.agent.query_raw(
                self.canister_id,
                "ggg_get_summary",
                encode([])  # No arguments
            )
            
            # Decode the result
            decoded = decode(result, [str])[0]
            logger.debug(f"Received summary: {decoded[:100]}...")
            return decoded
            
        except Exception as e:
            logger.error(f"Error getting realm summary: {str(e)}")
            return None
    
    def submit_proposal(self, proposal: Dict[str, str]) -> str:
        """Submit a proposal to the realm canister."""
        try:
            logger.info(f"Submitting proposal to canister {self.canister_id}")
            
            # Call the submit_proposal method on the canister
            result = self.agent.update_raw(
                self.canister_id,
                "submit_proposal",
                encode([proposal["title"], proposal["content"]])
            )
            
            # Decode the result
            decoded = decode(result, [str])[0]
            logger.info(f"Proposal submission result: {decoded}")
            return decoded
            
        except Exception as e:
            logger.error(f"Error submitting proposal: {str(e)}")
            raise RuntimeError(f"Failed to submit proposal: {str(e)}")
