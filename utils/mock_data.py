import json
import random
from datetime import datetime, timedelta, date
from typing import List, Dict
from models import Participant, Meeting

class MockDataGenerator:
    """Generate realistic mock data for testing"""
    
    def __init__(self):
        self.mock_participants = self._generate_mock_participants()
        self.mock_meetings = self._generate_mock_meetings()
    
    def _generate_mock_participants(self) -> List[Participant]:
        """Generate mock company directory"""
        participants = [
            Participant("john.smith@company.com", "John Smith", "Engineering", "Software Engineer"),
            Participant("sarah.johnson@company.com", "Sarah Johnson", "Marketing", "Marketing Manager"),
            Participant("mike.davis@company.com", "Mike Davis", "Sales", "Sales Representative"),
            Participant("emily.brown@company.com", "Emily Brown", "HR", "HR Manager"),
            Participant("david.wilson@company.com", "David Wilson", "Engineering", "Senior Developer"),
            Participant("lisa.anderson@company.com", "Lisa Anderson", "Finance", "Financial Analyst"),
            Participant("james.taylor@company.com", "James Taylor", "Operations", "Operations Manager"),
            Participant("maria.garcia@company.com", "Maria Garcia", "Design", "UX Designer"),
            Participant("robert.martinez@company.com", "Robert Martinez", "Engineering", "Tech Lead"),
            Participant("jennifer.lee@company.com", "Jennifer Lee", "Marketing", "Content Manager"),
            Participant("michael.johnson@company.com", "Michael Johnson", "Sales", "Account Executive"),
            Participant("sarah.davis@company.com", "Sarah Davis", "Engineering", "QA Engineer"),
            Participant("john.brown@company.com", "John Brown", "Finance", "Controller"),
            Participant("amy.wilson@company.com", "Amy Wilson", "HR", "Recruiter"),
            Participant("chris.miller@company.com", "Chris Miller", "Operations", "Project Manager"),
        ]
        
        # Set random availability status
        for p in participants:
            p.availability_status = random.choice(["available", "busy", "unknown"])
        
        return participants
    
    def _generate_mock_meetings(self) -> List[Meeting]:
        """Generate mock meetings for the past few days"""
        meetings = []
        base_date = datetime.now() - timedelta(days=7)
        
        meeting_titles = [
            "Daily Standup", "Sprint Planning", "Client Review", "Team Retrospective",
            "Project Kickoff", "Budget Meeting", "Training Session", "All Hands",
            "Design Review", "Code Review", "Strategy Meeting", "Performance Review"
        ]
        
        for i in range(20):
            meeting_date = base_date + timedelta(
                days=random.randint(0, 14),
                hours=random.randint(9, 17),
                minutes=random.choice([0, 30])
            )
            
            duration = random.choice([30, 60, 90, 120])
            participants = random.sample(self.mock_participants, random.randint(2, 5))
            
            meeting = Meeting(
                id=f"meeting_{i+1}",
                title=random.choice(meeting_titles),
                description=f"Auto-generated meeting {i+1}",
                organizer=participants[0].email,
                participants=participants,
                start_time=meeting_date,
                end_time=meeting_date + timedelta(minutes=duration),
                duration_minutes=duration,
                priority=random.choice(["low", "medium", "high"]),
                status=random.choice(["scheduled", "completed"]),
                created_at=meeting_date - timedelta(days=1)
            )
            meetings.append(meeting)
        
        return meetings
    
    def get_participants(self) -> List[Participant]:
        """Get all mock participants"""
        return self.mock_participants.copy()
    
    def get_meetings(self) -> List[Meeting]:
        """Get all mock meetings"""
        return self.mock_meetings.copy()
    
    def search_participants(self, query: str, limit: int = 10) -> List[Participant]:
        """Search participants by name or email"""
        query = query.lower().strip()
        if not query:
            return []
        
        matches = []
        for participant in self.mock_participants:
            # Check exact email match
            if query == participant.email.lower():
                matches.insert(0, participant)  # Exact email match goes first
                continue
            
            # Check if query appears in name or email
            name_match = query in participant.name.lower()
            email_match = query in participant.email.lower()
            
            if name_match or email_match:
                matches.append(participant)
        
        return matches[:limit]
    
    def get_participant_by_email(self, email: str) -> Participant:
        """Get participant by exact email match"""
        for participant in self.mock_participants:
            if participant.email.lower() == email.lower():
                return participant
        return None
    
    def get_availability(self, participant_emails: List[str], date_range: tuple) -> Dict[str, str]:
        """Get mock availability for participants in date range"""
        availability = {}
        for email in participant_emails:
            participant = self.get_participant_by_email(email)
            if participant:
                # Simulate some conflicts
                if random.random() < 0.3:  # 30% chance of conflict
                    availability[email] = "busy"
                else:
                    availability[email] = "available"
            else:
                availability[email] = "unknown"
        return availability
    
    def save_to_file(self, filename: str = "mock_data.json"):
        """Save mock data to JSON file"""
        data = {
            "participants": [p.to_dict() for p in self.mock_participants],
            "meetings": [m.to_dict() for m in self.mock_meetings]
        }
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
    
    def load_from_file(self, filename: str = "mock_data.json"):
        """Load mock data from JSON file"""
        try:
            with open(filename, 'r') as f:
                data = json.load(f)
            
            self.mock_participants = [
                Participant.from_dict(p) for p in data.get("participants", [])
            ]
            self.mock_meetings = [
                Meeting.from_dict(m) for m in data.get("meetings", [])
            ]
        except FileNotFoundError:
            # Use default generated data if file doesn't exist
            pass

# Global instance
mock_data = MockDataGenerator()
