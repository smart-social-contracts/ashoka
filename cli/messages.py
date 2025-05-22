"""
MCP Message Formats - Defines Multi-Canister Protocol message formats
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional
import json
from datetime import datetime


@dataclass
class ProposalOfferMessage:
    """Message sent by an AI governor offering a proposal to a realm."""
    type: str = "ProposalOffer"
    title: str = ""
    content: str = ""
    creator: str = ""
    price: int = 0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_json(self) -> str:
        """Convert the message to a JSON string."""
        return json.dumps(self.__dict__, indent=2)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'ProposalOfferMessage':
        """Create a message from a JSON string."""
        data = json.loads(json_str)
        return cls(**data)


@dataclass
class ProposalResponseMessage:
    """Message sent by a realm in response to a proposal offer."""
    type: str = "ProposalResponse"
    proposal_id: str = ""
    accepted: bool = False
    reason: str = ""
    payment_details: Optional[Dict[str, Any]] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_json(self) -> str:
        """Convert the message to a JSON string."""
        return json.dumps(self.__dict__, indent=2)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'ProposalResponseMessage':
        """Create a message from a JSON string."""
        data = json.loads(json_str)
        return cls(**data)


@dataclass
class PaymentReceiptMessage:
    """Message confirming payment for an accepted proposal."""
    type: str = "PaymentReceipt"
    proposal_id: str = ""
    payment_id: str = ""
    amount: int = 0
    token: str = ""
    sender: str = ""
    receiver: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_json(self) -> str:
        """Convert the message to a JSON string."""
        return json.dumps(self.__dict__, indent=2)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'PaymentReceiptMessage':
        """Create a message from a JSON string."""
        data = json.loads(json_str)
        return cls(**data)
