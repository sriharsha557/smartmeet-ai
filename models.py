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
        try:
            # Ensure required fields exist
            if 'email' not in data or 'name' not in data:
                raise ValueError("Participant must have email and name")
            
            return cls(
                email=str(data['email']),
                name=str(data['name']),
                department=data.get('department'),
                title=data.get('title'),
                availability_status=data.get('availability_status', 'unknown')
            )
        except (KeyError, TypeError, ValueError) as e:
            raise ValueError(f"Invalid participant data: {e}")

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
        try:
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
        except Exception as e:
            raise ValueError(f"Error converting meeting to dict: {e}")
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Meeting':
        try:
            # Create a copy to avoid modifying original data
            data_copy = data.copy()
            
            # Convert ISO strings back to datetime objects with error handling
            if data_copy.get('start_time'):
                try:
                    data_copy['start_time'] = datetime.fromisoformat(data_copy['start_time'])
                except (ValueError, TypeError):
                    data_copy['start_time'] = None
                    
            if data_copy.get('end_time'):
                try:
                    data_copy['end_time'] = datetime.fromisoformat(data_copy['end_time'])
                except (ValueError, TypeError):
                    data_copy['end_time'] = None
                    
            if data_copy.get('created_at'):
                try:
                    data_copy['created_at'] = datetime.fromisoformat(data_copy['created_at'])
                except (ValueError, TypeError):
                    data_copy['created_at'] = datetime.now()
                    
            if data_copy.get('updated_at'):
                try:
                    data_copy['updated_at'] = datetime.fromisoformat(data_copy['updated_at'])
                except (ValueError, TypeError):
                    data_copy['updated_at'] = datetime.now()
            
            # Convert participant dicts to objects with error handling
            if data_copy.get('participants'):
                participants = []
                for p in data_copy['participants']:
                    try:
                        if isinstance(p, dict):
                            participants.append(Participant.from_dict(p))
                        elif isinstance(p, Participant):
                            participants.append(p)
                    except Exception as e:
                        print(f"Warning: Skipping invalid participant: {e}")
                        continue
                data_copy['participants'] = participants
            else:
                data_copy['participants'] = []
            
            # Validate required fields and set defaults
            data_copy.setdefault('title', 'Untitled Meeting')
            data_copy.setdefault('description', '')
            data_copy.setdefault('duration_minutes', 60)
            data_copy.setdefault('priority', 'medium')
            data_copy.setdefault('status', 'draft')
            data_copy.setdefault('meeting_type', 'regular')
            
            return cls(**data_copy)
        except Exception as e:
            raise ValueError(f"Invalid meeting data: {e}")
    
    def add_participant(self, participant: Participant):
        """Add a participant to the meeting"""
        try:
            if participant and participant not in self.participants:
                self.participants.append(participant)
                self.updated_at = datetime.now()
        except Exception as e:
            raise ValueError(f"Error adding participant: {e}")
    
    def remove_participant(self, email: str):
        """Remove a participant by email"""
        try:
            original_count = len(self.participants)
            self.participants = [p for p in self.participants if p.email != email]
            if len(self.participants) < original_count:
                self.updated_at = datetime.now()
        except Exception as e:
            raise ValueError(f"Error removing participant: {e}")
    
    def get_participant_emails(self) -> List[str]:
        """Get list of participant emails"""
        try:
            return [p.email for p in self.participants if p and p.email]
        except Exception:
            return []

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
        try:
            data = asdict(self)
            if data['date_mentioned']:
                data['date_mentioned'] = self.date_mentioned.isoformat()
            return data
        except Exception as e:
            raise ValueError(f"Error converting parsed request to dict: {e}")

@dataclass
class ParticipantMatch:
    """Participant matching result"""
    query: str
    matches: List[Participant]
    confidence: float
    is_exact: bool = False
    is_email: bool = False
    
    def __post_init__(self):
        # Ensure matches is never None
        if self.matches is None:
            self.matches = []
        # Ensure confidence is within valid range
        self.confidence = max(0.0, min(1.0, self.confidence))
