from dataclasses import dataclass, asdict
from datetime import datetime, date
from typing import List, Optional, Dict, Any
import json

@dataclass
class Participant:
    """Participant data model"""
    email: str
    name: str
    department: Optional[str] = None
    title: Optional[str] = None
    availability_status: str = "unknown"  # available, busy, unknown
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Participant':
        return cls(**data)

@dataclass
class Meeting:
    """Meeting data model"""
    id: Optional[str] = None
    title: str = ""
    description: str = ""
    organizer: Optional[str] = None
    participants: List[Participant] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration_minutes: int = 60
    priority: str = "medium"  # low, medium, high, urgent
    status: str = "draft"  # draft, scheduled, completed, cancelled
    location: Optional[str] = None
    meeting_type: str = "regular"  # regular, recurring, all-day
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.participants is None:
            self.participants = []
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        # Convert datetime objects to ISO strings
        if data['start_time']:
            data['start_time'] = self.start_time.isoformat()
        if data['end_time']:
            data['end_time'] = self.end_time.isoformat()
        if data['created_at']:
            data['created_at'] = self.created_at.isoformat()
        if data['updated_at']:
            data['updated_at'] = self.updated_at.isoformat()
        # Convert participant objects to dicts
        data['participants'] = [p.to_dict() if isinstance(p, Participant) else p for p in data['participants']]
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Meeting':
        # Convert ISO strings back to datetime objects
        if data.get('start_time'):
            data['start_time'] = datetime.fromisoformat(data['start_time'])
        if data.get('end_time'):
            data['end_time'] = datetime.fromisoformat(data['end_time'])
        if data.get('created_at'):
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        if data.get('updated_at'):
            data['updated_at'] = datetime.fromisoformat(data['updated_at'])
        # Convert participant dicts to objects
        if data.get('participants'):
            data['participants'] = [
                Participant.from_dict(p) if isinstance(p, dict) else p 
                for p in data['participants']
            ]
        return cls(**data)
    
    def add_participant(self, participant: Participant):
        """Add a participant to the meeting"""
        if participant not in self.participants:
            self.participants.append(participant)
            self.updated_at = datetime.now()
    
    def remove_participant(self, email: str):
        """Remove a participant by email"""
        self.participants = [p for p in self.participants if p.email != email]
        self.updated_at = datetime.now()
    
    def get_participant_emails(self) -> List[str]:
        """Get list of participant emails"""
        return [p.email for p in self.participants]

@dataclass
class ParsedMeetingRequest:
    """Parsed natural language meeting request"""
    original_text: str
    title: Optional[str] = None
    participant_names: List[str] = None
    participant_emails: List[str] = None
    date_mentioned: Optional[date] = None
    time_mentioned: Optional[str] = None
    duration_mentioned: Optional[str] = None
    priority_mentioned: Optional[str] = None
    description: Optional[str] = None
    confidence: float = 0.0
    
    def __post_init__(self):
        if self.participant_names is None:
            self.participant_names = []
        if self.participant_emails is None:
            self.participant_emails = []
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        if data['date_mentioned']:
            data['date_mentioned'] = self.date_mentioned.isoformat()
        return data

@dataclass
class ParticipantMatch:
    """Participant matching result"""
    query: str
    matches: List[Participant]
    confidence: float
    is_exact: bool = False
    is_email: bool = False
