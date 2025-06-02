"""
Realm Interface Module - Handles interactions with GGG-compliant realm canisters
"""

import logging
import json
import subprocess
from typing import Dict, Optional

logger = logging.getLogger("ashoka.realm")

def run_command(command):
    """Run a shell command and return its output."""
    logger.debug(f"Running: {command}")
    process = subprocess.run(command, shell=True, capture_output=True, text=True)
    if process.returncode != 0:
        logger.error(f"Error executing command: {command}")
        logger.error(f"Error: {process.stderr}")
        return None
    return process.stdout.strip()

def get_current_principal():
    """Get the principal ID of the current identity."""
    principal = run_command("dfx identity get-principal")
    if not principal:
        raise Exception("Failed to get principal")
    return principal

class RealmInterface:
    """Interface for interacting with GGG-compliant realm canisters."""
    
    def __init__(self, canister_id: str, network_url: str = "https://ic0.app"):
        """Initialize the realm interface."""
        self.canister_id = canister_id
        self.network_url = network_url
        
        # Configure network in dfx if not using mainnet
        if network_url != "https://ic0.app":
            self.network_param = f"--network {network_url}"
        else:
            self.network_param = ""
        
        logger.info(f"RealmInterface initialized for canister: {canister_id}")
    
    def get_realm_data(self) -> Optional[str]:
        """Get a summary of the realm via the GGG interface."""
        try:
            logger.info(f"Querying get_realm_data from canister {self.canister_id}")
            
            # Call the get_realm_data method on the canister using dfx with JSON output
            command = f'dfx canister {self.network_param} call {self.canister_id} extension_sync_call \'(record {{ extension_name = "llm_chat"; function_name = "get_realm_data"; args = "none"; }})\' --output=json'
            result = run_command(command)
            
            if not result:
                logger.warning("Failed to get realm summary, returning mock summary")
                return "Mock realm summary: This is a simulated realm for testing purposes."
            
            # Parse the JSON result
            try:
                parsed_result = json.loads(result)
                # JSON output for a string is typically just the string itself
                summary = parsed_result[0] if isinstance(parsed_result, list) and len(parsed_result) > 0 else parsed_result
                logger.debug(f"Received summary: {str(summary)[:100]}...")
                return str(summary)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON response: {e}")
                return "Error parsing realm summary. Falling back to evaluation mode."
            
        except Exception as e:
            logger.error(f"Error getting realm summary: {str(e)}")
            return "Error fetching realm summary. Falling back to evaluation mode."
    
    def submit_proposal(self, proposal: Dict[str, str]) -> str:
        """Submit a proposal to the realm canister."""
        try:
            logger.info(f"Submitting proposal to canister {self.canister_id}")
            
            title = proposal["title"]
            content = proposal["content"]
            
            # Escape quotes in the title and content to avoid shell issues
            title = title.replace('"', '\\"')
            content = content.replace('"', '\\"')
            
            # Call the submit_proposal method on the canister using dfx with JSON output
            command = f'dfx canister {self.network_param} call {self.canister_id} submit_proposal "(\\""{title}\\", \\""{content}\\")" --output=json'
            result = run_command(command)
            
            if not result:
                logger.warning("Failed to submit proposal, returning mock result")
                return f"Mock submission successful: {proposal['title']} (Evaluation Mode)"
            
            # Parse the JSON result
            try:
                parsed_result = json.loads(result)
                # JSON output for a string is typically just the string itself
                response = parsed_result[0] if isinstance(parsed_result, list) and len(parsed_result) > 0 else parsed_result
                logger.info(f"Proposal submission result: {str(response)}")
                return str(response)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON response: {e}")
                return f"Error parsing submission result, but evaluation can continue: {str(e)}"
            
        except Exception as e:
            logger.error(f"Error submitting proposal: {str(e)}")
            return f"Error submitting proposal, but evaluation can continue: {str(e)}"
