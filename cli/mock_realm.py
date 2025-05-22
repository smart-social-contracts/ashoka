"""
Mock Realm Module - Provides a simulated realm environment for testing
"""

import logging
import json
import uuid
from typing import Dict, Any, Optional

logger = logging.getLogger("ashoka.mock_realm")

class MockRealm:
    """Mock implementation of a GGG-compliant realm for testing."""
    
    def __init__(self, config: Dict[str, Any] = None):
        """Initialize a mock realm with the given configuration."""
        self.config = config or {
            "name": "Test Realm",
            "members": 100,
            "treasury": 5000,
            "governance": {
                "voting_period": 3,
                "quorum": 0.3,
                "proposal_threshold": 5
            }
        }
        self.proposals = []
        logger.info(f"MockRealm initialized: {self.config['name']}")
    
    def get_summary(self) -> str:
        """
        Get a summary of the realm via the GGG interface.
        
        Returns:
            A string containing the realm summary
        """
        return f"""
        Realm: {self.config['name']}
        Members: {self.config['members']}
        Treasury: {self.config['treasury']} tokens
        
        Governance Configuration:
        - Voting Period: {self.config['governance']['voting_period']} days
        - Quorum: {self.config['governance']['quorum'] * 100}%
        - Proposal Threshold: {self.config['governance']['proposal_threshold']} tokens
        
        Active Proposals: {len([p for p in self.proposals if p['status'] == 'active'])}
        Historical Proposals: {len([p for p in self.proposals if p['status'] != 'active'])}
        """
    
    def submit_proposal(self, proposal: Dict[str, str]) -> str:
        """
        Submit a proposal to the mock realm.
        
        Args:
            proposal: Dictionary containing the proposal title and content
            
        Returns:
            Response from the mock realm
        """
        proposal_id = str(uuid.uuid4())
        
        # Add proposal to the realm's records
        self.proposals.append({
            "id": proposal_id,
            "title": proposal["title"],
            "content": proposal["content"],
            "status": "active",
            "votes_for": 0,
            "votes_against": 0,
            "timestamp": "2025-05-22T00:00:00Z"  # Using a fixed date for testing
        })
        
        logger.info(f"Proposal submitted to mock realm: {proposal['title']}")
        return f"Proposal submitted successfully. ID: {proposal_id}"
    
    def get_proposals(self, status: Optional[str] = None) -> Dict[str, Any]:
        """
        Get proposals from the mock realm.
        
        Args:
            status: Filter proposals by status (active, passed, rejected)
            
        Returns:
            Dictionary containing proposals
        """
        filtered_proposals = self.proposals
        if status:
            filtered_proposals = [p for p in self.proposals if p["status"] == status]
            
        return {
            "proposals": filtered_proposals,
            "total": len(filtered_proposals)
        }
    
    def vote_on_proposal(self, proposal_id: str, vote: bool, amount: int = 1) -> str:
        """
        Vote on a proposal in the mock realm.
        
        Args:
            proposal_id: ID of the proposal to vote on
            vote: True for yes/for, False for no/against
            amount: Voting power to apply
            
        Returns:
            Response from the mock realm
        """
        for proposal in self.proposals:
            if proposal["id"] == proposal_id:
                if vote:
                    proposal["votes_for"] += amount
                else:
                    proposal["votes_against"] += amount
                
                # Check if proposal has passed or failed
                total_votes = proposal["votes_for"] + proposal["votes_against"]
                if total_votes >= self.config["members"] * self.config["governance"]["quorum"]:
                    if proposal["votes_for"] > proposal["votes_against"]:
                        proposal["status"] = "passed"
                    else:
                        proposal["status"] = "rejected"
                
                return f"Vote recorded for proposal {proposal_id}. Current status: {proposal['status']}"
        
        return f"Proposal {proposal_id} not found"
