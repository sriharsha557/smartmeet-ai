import re
from datetime import datetime, date, timedelta
from typing import List, Optional
from models import ParsedMeetingRequest

class SimpleNLPService:
    """Simple fallback NLP service without NLTK dependencies"""
    
    def __init__(self):
        self._init_patterns()
    
    def _init_patterns(self):
        """Initialize regex patterns for parsing"""
        # Time patterns
        self.time_patterns = [
            r'(?i)(?:at\s+)?(\d{1,2}):?(\d{0,2})\s*(am|pm)',
            r'(?i)(?:at\s+)?(\d{1,2})\s*(am|pm)',
            r'(?i)(\d{1,2}):(\d{2})',
        ]
        
        # Date patterns
        self.date_patterns = [
            r'(?i)(today|tomorrow|yesterday)',
            r'(?i)(monday|tuesday|wednesday|thursday|friday|saturday|sunday)',
            r'(?i)(next|this)\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)',
        ]
        
        # Duration patterns
        self.duration_patterns = [
            r'(?i)(\d+)\s*hours?\s*(\d+)?\s*minutes?',
            r'(?i)(\d+)\s*hours?',
            r'(?i)(\d+)\s*minutes?',
            r'(?i)(half|1/2)\s*hour',
        ]
        
        # Priority patterns
        self.priority_patterns = [
            r'(?i)(urgent|asap|immediately|critical)',
            r'(?i)(high|important)\s*priority',
            r'(?i)(low|normal)\s*priority',
        ]
        
        # Email patterns
        self.email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        
        # Meeting keywords
        self.meeting_keywords = [
            'meeting', 'call', 'sync', 'standup', 'review', 'discussion'
        ]
    
    def parse_meeting_request(self, text: str) -> ParsedMeetingRequest:
        """Parse natural language meeting request using simple regex"""
        text = text.strip()
        if not text:
            return ParsedMeetingRequest(original_text=text, confidence=0.0)
        
        parsed = ParsedMeetingRequest(original_text=text)
        
        # Extract components
        parsed.participant_names = self._extract_names(text)
        parsed.participant_emails = self._extract_emails(text)
        parsed.date_mentioned = self._extract_date(text)
        parsed.time_mentioned = self._extract_time(text)
        parsed.duration_mentioned = self._extract_duration(text)
        parsed.priority_mentioned = self._extract_priority(text)
        parsed.title = self._extract_title(text)
        parsed.description = text if len(text) > 20 else None
        
        # Calculate confidence
        parsed.confidence = self._calculate_confidence(parsed)
        
        return parsed
    
    def _extract_names(self, text: str) -> List[str]:
        """Extract participant names using simple patterns"""
        names = []
        
        # Look for patterns like "with John", "and Sarah"
        patterns = [
            r'(?i)with\s+([A-Z][a-z]+)',
            r'(?i)and\s+([A-Z][a-z]+)',
            r'(?i)([A-Z][a-z]+)\s+and',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text)
            names.extend(matches)
        
        return list(set(names))  # Remove duplicates
    
    def _extract_emails(self, text: str) -> List[str]:
        """Extract email addresses"""
        emails = re.findall(self.email_pattern, text)
        return list(set(emails))
    
    def _extract_date(self, text: str) -> Optional[date]:
        """Extract date from text"""
        today = date.today()
        
        if re.search(r'(?i)\btoday\b', text):
            return today
        elif re.search(r'(?i)\btomorrow\b', text):
            return today + timedelta(days=1)
        elif re.search(r'(?i)\byesterday\b', text):
            return today - timedelta(days=1)
        
        # Day names
        days_of_week = {
            'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
            'friday': 4, 'saturday': 5, 'sunday': 6
        }
        
        for day_name, day_num in days_of_week.items():
            if re.search(rf'(?i)\b{day_name}\b', text):
                days_ahead = day_num - today.weekday()
                if days_ahead <= 0:
                    days_ahead += 7
                return today + timedelta(days=days_ahead)
        
        return None
    
    def _extract_time(self, text: str) -> Optional[str]:
        """Extract time from text"""
        for pattern in self.time_patterns:
            match = re.search(pattern, text)
            if match:
                groups = match.groups()
                if len(groups) == 3:  # HH:MM AM/PM
                    hour, minute, period = groups
                    minute = minute or "00"
                    return f"{hour}:{minute} {period.upper()}"
                elif len(groups) == 2:
                    if groups[1].lower() in ['am', 'pm']:  # H AM/PM
                        hour, period = groups
                        return f"{hour}:00 {period.upper()}"
        return None
    
    def _extract_duration(self, text: str) -> Optional[str]:
        """Extract duration from text"""
        if re.search(r'(?i)(half|1/2)\s*hour', text):
            return "30 minutes"
        
        hour_match = re.search(r'(?i)(\d+)\s*hours?', text)
        if hour_match:
            hours = int(hour_match.group(1))
            return f"{hours} hour{'s' if hours > 1 else ''}"
        
        minute_match = re.search(r'(?i)(\d+)\s*minutes?', text)
        if minute_match:
            minutes = int(minute_match.group(1))
            return f"{minutes} minutes"
        
        return None
    
    def _extract_priority(self, text: str) -> Optional[str]:
        """Extract priority from text"""
        if re.search(r'(?i)(urgent|asap|critical)', text):
            return "urgent"
        elif re.search(r'(?i)(high|important)', text):
            return "high"
        elif re.search(r'(?i)(low|normal)', text):
            return "low"
        return None
    
    def _extract_title(self, text: str) -> Optional[str]:
        """Extract or generate meeting title"""
        # Look for meeting keywords
        for keyword in self.meeting_keywords:
            if keyword in text.lower():
                return f"{keyword.title()}"
        
        # Use first few words
        words = text.split()[:3]
        return ' '.join(words).title() if len(words) >= 2 else "New Meeting"
    
    def _calculate_confidence(self, parsed: ParsedMeetingRequest) -> float:
        """Calculate confidence score"""
        confidence = 0.0
        
        if parsed.original_text:
            confidence += 0.1
        if parsed.participant_names or parsed.participant_emails:
            confidence += 0.3
        if parsed.date_mentioned:
            confidence += 0.3
        if parsed.time_mentioned:
            confidence += 0.2
        if any(keyword in parsed.original_text.lower() for keyword in self.meeting_keywords):
            confidence += 0.1
        
        return min(confidence, 1.0)

# Global instance
simple_nlp_service = SimpleNLPService()
