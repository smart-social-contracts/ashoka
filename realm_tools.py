#!/usr/bin/env python3
"""
Realm Tools - Functions that Ashoka LLM can call to explore realm data
"""
import subprocess
import json
import traceback
from typing import Optional


def db_get(entity_type: str, network: str = "staging", realm_folder: str = "../realms/examples/demo/realm1") -> str:
    """
    Get entities from the realm database.
    
    Args:
        entity_type: Type of entity to query (User, Proposal, Vote, Transfer, Mandate, Task, Organization)
        network: Network to query (local, staging, ic)
        realm_folder: Path to realm folder containing dfx.json
    
    Returns:
        JSON string of entities found
    """
    import os
    cmd = ["realms", "db", "-f", realm_folder, "-n", network, "get", entity_type]
    
    # Set environment to suppress DFX security warnings for read-only operations
    env = os.environ.copy()
    env['DFX_WARNING'] = '-mainnet_plaintext_identity'
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, env=env)
        if result.returncode == 0:
            return result.stdout.strip() or "No entities found"
        else:
            return f"Error: {result.stderr.strip()}"
    except subprocess.TimeoutExpired:
        return "Error: Command timed out"
    except Exception as e:
        traceback.print_exc()
        return f"Error: {str(e)}"


def realm_status(network: str = "local", realm_folder: str = ".") -> str:
    """
    Get the current status of a realm (users count, proposals, votes, etc.).
    
    Args:
        network: Network to query (local, staging, ic)
        realm_folder: Path to realm folder containing dfx.json
    
    Returns:
        JSON string with realm status including counts for users, proposals, votes, etc.
    """
    import os
    cmd = ["realms", "realm", "call", "status", "-n", network]
    
    # Set environment to suppress DFX security warnings for read-only operations
    env = os.environ.copy()
    env['DFX_WARNING'] = '-mainnet_plaintext_identity'
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, cwd=realm_folder, env=env)
        if result.returncode == 0:
            return result.stdout.strip() or "No status available"
        else:
            return f"Error: {result.stderr.strip()}"
    except subprocess.TimeoutExpired:
        return "Error: Command timed out"
    except Exception as e:
        traceback.print_exc()
        return f"Error: {str(e)}"


# Tool definitions for Ollama (OpenAI-compatible format)
REALM_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "db_get",
            "description": "Get entities from the realm database. Use this to look up users, proposals, votes, transfers, mandates, tasks, or organizations in a realm.",
            "parameters": {
                "type": "object",
                "properties": {
                    "entity_type": {
                        "type": "string",
                        "description": "Type of entity to query from the realm database",
                        "enum": ["Balance", "Call", "Codex", "Contract", "Dispute", "Human", "Identity", "Instrument", "Invoice", "Land", "License", "Mandate", "Member", "Notification", "Organization", "PaymentAccount", "Permission", "Proposal", "Realm", "Registry", "Service", "Status", "Task", "TaskExecution", "TaskSchedule", "TaskStep", "Trade", "Transfer", "Treasury", "User", "UserProfile", "Vote"]
                    }
                },
                "required": ["entity_type"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "realm_status",
            "description": "Get the current status of the realm including counts for users, proposals, votes, transfers, mandates, tasks, organizations, and installed extensions.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    }
]

# Map function names to actual functions
TOOL_FUNCTIONS = {
    "db_get": db_get,
    "realm_status": realm_status
}


def execute_tool(tool_name: str, arguments: dict, network: str = "staging", realm_folder: str = "../realms/examples/demo/realm1") -> str:
    """Execute a tool by name with given arguments."""
    if tool_name not in TOOL_FUNCTIONS:
        return f"Error: Unknown tool '{tool_name}'"
    
    # Filter to only valid arguments for the function
    func = TOOL_FUNCTIONS[tool_name]
    import inspect
    valid_params = set(inspect.signature(func).parameters.keys())
    
    # Start with network and realm_folder defaults
    filtered_args = {
        "network": network,
        "realm_folder": realm_folder
    }
    
    # Add any valid arguments from the LLM
    for key, value in arguments.items():
        if key in valid_params:
            filtered_args[key] = value
    
    return func(**filtered_args)
