"""
Realm Interface Module - Handles interactions with GGG-compliant realm canisters
"""

import logging
import os
import json
import subprocess
from typing import Dict, Optional

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("ashoka.realm")
logger.setLevel(logging.DEBUG)

def run_command(command):
    """Run a shell command and return its output."""
    logger.debug(f"Running command: {command}")
    try:
        process = subprocess.run(command, shell=True, capture_output=True, text=True)
        logger.debug(f"Command exit code: {process.returncode}")
        
        if process.returncode != 0:
            logger.error(f"Error executing command: {command}")
            logger.error(f"Error: {process.stderr}")
            return None
            
        logger.debug(f"Command stdout: {process.stdout[:500]}")
        if len(process.stdout) > 500:
            logger.debug("Output truncated...")
            
        return process.stdout.strip()
    except Exception as e:
        logger.exception(f"Exception executing command: {e}")
        return None

def get_current_principal():
    """Get the principal ID of the current identity."""
    logger.debug("Getting current principal")
    principal = run_command("dfx identity get-principal")
    if not principal:
        logger.error("Failed to get principal")
        raise Exception("Failed to get principal")
    logger.debug(f"Current principal: {principal}")
    return principal

class RealmInterface:
    """Interface for interacting with GGG-compliant realm canisters."""
    
    def __init__(self, canister_id: str, network_url: str = "https://ic0.app"):
        """Initialize the realm interface."""
        self.canister_id = canister_id
        
        # Get network from environment variable if set, otherwise use the provided network_url
        network = os.environ.get('ASHOKA_DFX_NETWORK')
        if network:
            self.network_param = f"--network {network}"
            logger.debug(f"Using network from ASHOKA_DFX_NETWORK: {network}, network_param: {self.network_param}")
        else:
            self.network_param = ""
            logger.debug(f"No ASHOKA_DFX_NETWORK set, using default network")
        
        logger.info(f"RealmInterface initialized for canister: {canister_id} on network: {self.network_param}")
    
    def get_realm_data(self) -> Optional[str]:
        """Get a summary of the realm via the GGG interface."""
        logger.debug(f"Querying get_realm_data from canister {self.canister_id}")
        try:
            logger.info(f"Querying get_realm_data from canister {self.canister_id}")
            
            # Call the get_realm_data method on the canister using dfx with JSON output
            command = f'dfx canister {self.network_param} call {self.canister_id} extension_sync_call \'(record {{ extension_name = "llm_chat"; function_name = "get_realm_data"; args = "none"; }})\' --output=json'
            logger.debug(f"Running command: {command}")
            result = run_command(command)
            logger.debug(f"Received result: {result}")
            
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
        logger.debug(f"Submitting proposal to canister {self.canister_id}")
        try:
            logger.info(f"Submitting proposal to canister {self.canister_id}")
            
            title = proposal["title"]
            content = proposal["content"]
            
            # Escape quotes in the title and content to avoid shell issues
            title = title.replace('"', '\\"')
            content = content.replace('"', '\\"')
            
            # Call the submit_proposal method on the canister using dfx with JSON output
            command = f'dfx canister {self.network_param} call {self.canister_id} submit_proposal "(\\""{title}\\", \\""{content}\\")" --output=json'
            logger.info(f"Running command: {command}")
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
