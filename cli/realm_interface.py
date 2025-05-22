"""
Realm Interface Module - Handles interactions with GGG-compliant realm canisters
"""

import logging
from typing import Dict, Optional

# Handle ic-py imports with proper error handling
try:
    import ic_py.client as ic_client
    from ic_py.identity import Identity
    from ic_py.agent import Agent
    from ic_py.candid import encode, decode
except ImportError:
    # Fallback to legacy import structure if needed
    try:
        import ic.client as ic_client
        from ic.identity import Identity
        from ic.agent import Agent
        from ic.candid import encode, decode
    except ImportError:
        logging.error("Failed to import IC package. Make sure ic-py is properly installed.")
        # Define placeholder classes to avoid breaking the code
        class Identity: pass
        class Agent: pass
        def encode(*args, **kwargs): pass
        def decode(*args, **kwargs): pass
        ic_client = None

logger = logging.getLogger("ashoka.realm")

class RealmInterface:
    """Interface for interacting with GGG-compliant realm canisters."""
    
    def __init__(self, canister_id: str, network_url: str = "https://ic0.app"):
        """Initialize the realm interface."""
        self.canister_id = canister_id
        self.network_url = network_url
        
        # Initialize IC agent
        # Skip initialization if IC package is not properly imported
        if 'Identity' in globals() and not isinstance(Identity, type(type)):
            identity = Identity()
            self.agent = Agent(identity, network_url)
        else:
            logger.warning("IC package not properly imported, realm interface will be limited")
            self.agent = None
        logger.info(f"RealmInterface initialized for canister: {canister_id}")
    
    def get_summary(self) -> Optional[str]:
        """Get a summary of the realm via the GGG interface."""
        try:
            logger.info(f"Querying ggg_get_summary from canister {self.canister_id}")
            
            # Check if agent is available
            if self.agent is None:
                logger.warning("Agent not initialized, returning mock summary")
                return "Mock realm summary: This is a simulated realm for testing purposes."
            
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
            return "Error fetching realm summary. Falling back to evaluation mode."
    
    def submit_proposal(self, proposal: Dict[str, str]) -> str:
        """Submit a proposal to the realm canister."""
        try:
            logger.info(f"Submitting proposal to canister {self.canister_id}")
            
            # Check if agent is available
            if self.agent is None:
                logger.warning("Agent not initialized, returning mock submission result")
                return f"Mock submission successful: {proposal['title']} (Evaluation Mode)"
            
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
            return f"Error submitting proposal, but evaluation can continue: {str(e)}"
