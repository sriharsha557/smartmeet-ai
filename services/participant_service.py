from typing import List, Dict, Optional, Tuple
from models import Participant, ParticipantMatch
from utils.mock_data import mock_data
import re

class ParticipantService:
    """Service for resolving and managing participants"""
    
    def __init__(self):
        self.mock_data = mock_data
    
    def resolve_participants(self, names: List[str], emails: List[str]) -> List[ParticipantMatch]:
        """Resolve participant names and emails to actual participants"""
        matches = []
        
        # Process emails first (exact matches)
        for email in emails:
            if self._is_valid_email(email):
                participant = self.mock_data.get_participant_by_email(email)
                if participant:
                    match = ParticipantMatch(
                        query=email,
                        matches=[participant],
                        confidence=1.0,
                        is_exact=True,
                        is_email=True
                    )
                else:
                    # Create new participant for unknown email
                    new_participant = Participant(email=email, name=self._extract_name_from_email(email))
                    match = ParticipantMatch(
                        query=email,
                        matches=[new_participant],
                        confidence=0.8,
                        is_exact=False,
                        is_email=True
                    )
                matches.append(match)
        
        # Process names (fuzzy matching)
        for name in names:
            if name and len(name.strip()) > 1:
                found_matches = self._search_participants_by_name(name)
                confidence = self._calculate_name_confidence(name, found_matches)
                
                match = ParticipantMatch(
                    query=name,
                    matches=found_matches,
                    confidence=confidence,
                    is_exact=len(found_matches) == 1 and self._is_exact_name_match(name, found_matches[0]),
                    is_email=False
                )
                matches.append(match)
        
        return matches
    
    def _is_valid_email(self, email: str) -> bool:
        """Check if string is a valid email format"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    def _extract_name_from_email(self, email: str) -> str:
        """Extract a display name from email address"""
        local_part = email.split('@')[0]
        # Replace dots and underscores with spaces, title case
        name = local_part.replace('.', ' ').replace('_', ' ').title()
        return name
    
    def _search_participants_by_name(self, name: str) -> List[Participant]:
        """Search for participants by name using fuzzy matching"""
        name = name.lower().strip()
        if not name:
            return []
        
        participants = self.mock_data.get_participants()
        matches = []
        
        for participant in participants:
            participant_name = participant.name.lower()
            
            # Exact match
            if name == participant_name:
                matches.insert(0, participant)
                continue
            
            # First name match
            first_name = participant_name.split()[0]
            if name == first_name:
                matches.append(participant)
                continue
            
            # Last name match
            name_parts = participant_name.split()
            if len(name_parts) > 1 and name == name_parts[-1]:
                matches.append(participant)
                continue
            
            # Partial match
            if name in participant_name or participant_name in name:
                matches.append(participant)
                continue
            
            # Check if any word in the query matches any word in the participant name
            query_words = name.split()
            name_words = participant_name.split()
            if any(qw in nw or nw in qw for qw in query_words for nw in name_words):
                matches.append(participant)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_matches = []
        for match in matches:
            if match.email not in seen:
                seen.add(match.email)
                unique_matches.append(match)
        
        return unique_matches[:10]  # Limit to top 10 matches
    
    def _calculate_name_confidence(self, query: str, matches: List[Participant]) -> float:
        """Calculate confidence score for name matching"""
        if not matches:
            return 0.0
        
        query = query.lower().strip()
        best_match = matches[0]
        best_name = best_match.name.lower()
        
        # Exact match
        if query == best_name:
            return 1.0
        
        # First name exact match
        first_name = best_name.split()[0]
        if query == first_name:
            return 0.9 if len(matches) == 1 else 0.7
        
        # Last name exact match
        name_parts = best_name.split()
        if len(name_parts) > 1 and query == name_parts[-1]:
            return 0.8 if len(matches) == 1 else 0.6
        
        # Partial match
        if query in best_name or best_name in query:
            return 0.7 if len(matches) == 1 else 0.5
        
        # Word overlap
        query_words = set(query.split())
        name_words = set(best_name.split())
        overlap = len(query_words & name_words)
        if overlap > 0:
            return min(0.6, 0.3 + (overlap * 0.1))
        
        return 0.3  # Some match found but low confidence
    
    def _is_exact_name_match(self, query: str, participant: Participant) -> bool:
        """Check if the query exactly matches the participant name"""
        return query.lower().strip() == participant.name.lower().strip()
    
    def get_participant_suggestions(self, partial_name: str, limit: int = 5) -> List[Participant]:
        """Get participant suggestions for autocomplete"""
        return self.mock_data.search_participants(partial_name, limit)
    
    def validate_participant_list(self, participants: List[Participant]) -> Dict[str, List[str]]:
        """Validate a list of participants and return any issues"""
        issues = {
            'invalid_emails': [],
            'duplicates': [],
            'missing_info': []
        }
        
        seen_emails = set()
        for participant in participants:
            # Check for invalid emails
            if not self._is_valid_email(participant.email):
                issues['invalid_emails'].append(participant.email)
            
            # Check for duplicates
            if participant.email.lower() in seen_emails:
                issues['duplicates'].append(participant.email)
            else:
                seen_emails.add(participant.email.lower())
            
            # Check for missing information
            if not participant.name or not participant.name.strip():
                issues['missing_info'].append(f"Missing name for {participant.email}")
        
        return issues
    
    def add_external_participant(self, email: str, name: str = None) -> Participant:
        """Add an external participant (not in company directory)"""
        if not self._is_valid_email(email):
            raise ValueError(f"Invalid email format: {email}")
        
        if not name:
            name = self._extract_name_from_email(email)
        
        participant = Participant(
            email=email,
            name=name,
            department="External",
            title="External Participant",
            availability_status="unknown"
        )
        
        return participant
    
    def get_availability_summary(self, participants: List[Participant], date_str: str = None) -> Dict[str, str]:
        """Get availability summary for participants"""
        if not date_str:
            # Use mock availability
            emails = [p.email for p in participants]
            return self.mock_data.get_availability(emails, (None, None))
        
        # For specific dates, simulate more realistic availability
        availability = {}
        for participant in participants:
            if participant.department == "External":
                availability[participant.email] = "unknown"
            else:
                # Simulate availability based on mock data
                availability[participant.email] = participant.availability_status
        
        return availability

# Global instance
participant_service = ParticipantService()
