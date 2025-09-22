import re
import nltk
from datetime import datetime, date, timedelta
from typing import List, Optional, Dict, Tuple
from models import ParsedMeetingRequest
import calendar

class NLPService:
    """Natural Language Processing for meeting requests"""
    
    def __init__(self):
        self._ensure_nltk_data()
        self._init_patterns()
    
    def _ensure_nltk_data(self):
        """Ensure required NLTK data is downloaded"""
        try:
            import nltk.data
            nltk.data.find('tokenizers/punkt')
            nltk.data.find('corpora/stopwords')
        except (LookupError, ImportError):
            try:
                import ssl
                try:
                    _create_unverified_https_context = ssl._create_unverified_context
                except AttributeError:
                    pass
                else:
                    ssl._create_default_https_context = _create_unverified_https_context
                
                nltk.download('punkt', quiet=True)
                nltk.download('stopwords', quiet=True)
            except Exception as e:
                # Complete fallback - NLTK functionality will be limited
                print(f"Warning: NLTK data download failed: {e}. Using basic text processing.")
    
    def _init_patterns(self):
        """Initialize regex patterns for parsing"""
        # Time patterns - improved with better error handling
        self.time_patterns = [
            r'(?i)(?:at\s+)?(\d{1,2}):(\d{2})\s*(am|pm)',
            r'(?i)(?:at\s+)?(\d{1,2})\s*(am|pm)',
            r'(?i)(?:at\s+)?(\d{1,2}):(\d{2})',
        ]
        
        # Date patterns
        self.date_patterns = [
            r'(?i)(today|tomorrow|yesterday)',
            r'(?i)(monday|tuesday|wednesday|thursday|friday|saturday|sunday)',
            r'(?i)(next|this)\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)',
            r'(?i)(january|february|march|april|may|june|july|august|september|october|november|december)\s+(\d{1,2})',
            r'(?i)(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{2,4})',
            r'(?i)(\d{1,2})[\/\-](\d{1,2})',
        ]
        
        # Duration patterns
        self.duration_patterns = [
            r'(?i)(\d+(?:\.\d+)?)\s*hours?\s*(\d+)?\s*minutes?',
            r'(?i)(\d+(?:\.\d+)?)\s*hours?',
            r'(?i)(\d+)\s*minutes?',
            r'(?i)(\d+)\s*mins?',
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
        
        # Common meeting keywords
        self.meeting_keywords = [
            'meeting', 'call', 'sync', 'standup', 'review', 'discussion',
            'session', 'presentation', 'demo', 'interview', 'chat'
        ]
    
    def parse_meeting_request(self, text: str) -> ParsedMeetingRequest:
        """Parse natural language meeting request"""
        text = text.strip()
        if not text:
            return ParsedMeetingRequest(original_text=text, confidence=0.0)
        
        parsed = ParsedMeetingRequest(original_text=text)
        
        try:
            # Extract components with error handling
            parsed.participant_names = self._extract_participant_names(text)
            parsed.participant_emails = self._extract_emails(text)
            parsed.date_mentioned = self._extract_date(text)
            parsed.time_mentioned = self._extract_time(text)
            parsed.duration_mentioned = self._extract_duration(text)
            parsed.priority_mentioned = self._extract_priority(text)
            parsed.title = self._extract_title(text)
            parsed.description = self._extract_description(text)
            
            # Calculate confidence
            parsed.confidence = self._calculate_confidence(parsed)
        except Exception as e:
            print(f"Warning: Error parsing meeting request: {e}")
            parsed.confidence = 0.1  # Low confidence due to parsing error
        
        return parsed
    
    def _extract_participant_names(self, text: str) -> List[str]:
        """Extract participant names from text"""
        names = []
        
        # Look for patterns like "with John", "and Sarah", "John and Mary"
        patterns = [
            r'(?i)with\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
            r'(?i)and\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
            r'(?i)([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+and',
            r'(?i),\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
        ]
        
        for pattern in patterns:
            try:
                matches = re.findall(pattern, text)
                names.extend(matches)
            except Exception:
                continue
        
        # Look for standalone names (common first names)
        common_names = [
            'John', 'Jane', 'Mike', 'Sarah', 'David', 'Emily', 'Chris', 'Lisa',
            'James', 'Maria', 'Robert', 'Jennifer', 'Michael', 'Amy', 'Daniel',
            'Jessica', 'Matthew', 'Ashley', 'Andrew', 'Amanda'
        ]
        
        words = text.split()
        for word in words:
            if word in common_names and word not in names:
                names.append(word)
        
        # Remove duplicates while preserving order
        return list(dict.fromkeys(names))
    
    def _extract_emails(self, text: str) -> List[str]:
        """Extract email addresses from text"""
        try:
            emails = re.findall(self.email_pattern, text)
            return list(set(emails))  # Remove duplicates
        except Exception:
            return []
    
    def _extract_date(self, text: str) -> Optional[date]:
        """Extract date from text with better error handling"""
        try:
            today = date.today()
            
            # Relative dates
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
                    if days_ahead <= 0:  # Target day already happened this week
                        days_ahead += 7
                    return today + timedelta(days=days_ahead)
            
            # Next/this + day name
            for day_name, day_num in days_of_week.items():
                if re.search(rf'(?i)\b(?:next|this)\s+{day_name}\b', text):
                    days_ahead = day_num - today.weekday()
                    if days_ahead <= 0:
                        days_ahead += 7
                    return today + timedelta(days=days_ahead)
            
            # Month day patterns
            months = {
                'january': 1, 'february': 2, 'march': 3, 'april': 4,
                'may': 5, 'june': 6, 'july': 7, 'august': 8,
                'september': 9, 'october': 10, 'november': 11, 'december': 12
            }
            
            for month_name, month_num in months.items():
                match = re.search(rf'(?i)\b{month_name}\s+(\d{{1,2}})\b', text)
                if match:
                    try:
                        day = int(match.group(1))
                        year = today.year
                        # If the month has passed this year, assume next year
                        if month_num < today.month or (month_num == today.month and day < today.day):
                            year += 1
                        return date(year, month_num, day)
                    except (ValueError, OverflowError):
                        continue
            
            # Date formats like MM/DD or MM/DD/YYYY
            date_match = re.search(r'(\d{1,2})[\/\-](\d{1,2})(?:[\/\-](\d{2,4}))?', text)
            if date_match:
                try:
                    month = int(date_match.group(1))
                    day = int(date_match.group(2))
                    year = int(date_match.group(3)) if date_match.group(3) else today.year
                    if year < 100:
                        year += 2000
                    return date(year, month, day)
                except (ValueError, OverflowError):
                    pass
            
        except Exception as e:
            print(f"Warning: Error extracting date: {e}")
        
        return None
    
    def _extract_time(self, text: str) -> Optional[str]:
        """Extract time from text with improved error handling"""
        try:
            for pattern in self.time_patterns:
                match = re.search(pattern, text)
                if match:
                    groups = match.groups()
                    
                    if len(groups) == 3:  # HH:MM AM/PM
                        hour, minute, period = groups
                        try:
                            hour_int = int(hour)
                            minute_int = int(minute) if minute else 0
                            
                            # Validate hour and minute ranges
                            if 1 <= hour_int <= 12 and 0 <= minute_int <= 59:
                                return f"{hour_int}:{minute_int:02d} {period.upper()}"
                        except ValueError:
                            continue
                    
                    elif len(groups) == 2:
                        if groups[1].lower() in ['am', 'pm']:  # H AM/PM
                            hour, period = groups
                            try:
                                hour_int = int(hour)
                                if 1 <= hour_int <= 12:
                                    return f"{hour_int}:00 {period.upper()}"
                            except ValueError:
                                continue
                        else:  # HH:MM (24 hour)
                            hour, minute = groups
                            try:
                                hour_int = int(hour)
                                minute_int = int(minute)
                                
                                if 0 <= hour_int <= 23 and 0 <= minute_int <= 59:
                                    if hour_int > 12:
                                        return f"{hour_int - 12}:{minute_int:02d} PM"
                                    elif hour_int == 12:
                                        return f"12:{minute_int:02d} PM"
                                    elif hour_int == 0:
                                        return f"12:{minute_int:02d} AM"
                                    else:
                                        return f"{hour_int}:{minute_int:02d} AM"
                            except ValueError:
                                continue
        except Exception as e:
            print(f"Warning: Error extracting time: {e}")
        
        return None
    
    def _extract_duration(self, text: str) -> Optional[str]:
        """Extract duration from text with better error handling"""
        try:
            for pattern in self.duration_patterns:
                match = re.search(pattern, text)
                if match:
                    match_text = match.group(0).lower()
                    
                    if 'half' in match_text or '1/2' in match_text:
                        return "30 minutes"
                    
                    elif 'hour' in match_text:
                        try:
                            hours = float(match.group(1))
                            minutes = int(match.group(2)) if len(match.groups()) > 1 and match.group(2) else 0
                            
                            if hours == 1 and minutes == 0:
                                return "1 hour"
                            elif hours == 1.5 or (hours == 1 and minutes == 30):
                                return "1.5 hours"
                            elif hours == 2 and minutes == 0:
                                return "2 hours"
                            else:
                                total_minutes = int(hours * 60) + minutes
                                if total_minutes <= 0:
                                    continue
                                return f"{total_minutes} minutes"
                        except (ValueError, OverflowError):
                            continue
                    
                    elif 'minute' in match_text or 'min' in match_text:
                        try:
                            minutes = int(match.group(1))
                            if minutes > 0:
                                return f"{minutes} minutes"
                        except (ValueError, OverflowError):
                            continue
        except Exception as e:
            print(f"Warning: Error extracting duration: {e}")
        
        return None
    
    def _extract_priority(self, text: str) -> Optional[str]:
        """Extract priority from text"""
        try:
            for pattern in self.priority_patterns:
                match = re.search(pattern, text)
                if match:
                    priority_text = match.group(1).lower()
                    if priority_text in ['urgent', 'asap', 'immediately', 'critical']:
                        return "urgent"
                    elif priority_text in ['high', 'important']:
                        return "high"
                    elif priority_text in ['low', 'normal']:
                        return "low"
        except Exception as e:
            print(f"Warning: Error extracting priority: {e}")
        
        return None
    
    def _extract_title(self, text: str) -> Optional[str]:
        """Extract or generate meeting title"""
        try:
            # Look for quoted strings that might be titles
            quoted_matches = re.findall(r'"([^"]*)"', text)
            if quoted_matches and quoted_matches[0].strip():
                return quoted_matches[0].strip()
            
            # Look for meeting keywords and use surrounding context
            for keyword in self.meeting_keywords:
                if keyword in text.lower():
                    # Try to find a descriptive phrase around the keyword
                    pattern = rf'(?i)(\w+\s+)?{keyword}(\s+\w+)?'
                    match = re.search(pattern, text)
                    if match:
                        title = match.group(0).strip()
                        if len(title) > 5:  # Avoid single words
                            return title.title()
            
            # Fallback: use first few words if no specific title found
            words = text.split()[:5]
            if len(words) >= 2:
                return ' '.join(words).title()
        except Exception as e:
            print(f"Warning: Error extracting title: {e}")
        
        return None
    
    def _extract_description(self, text: str) -> Optional[str]:
        """Extract description or use the full text as description"""
        try:
            # For now, use the original text as description
            # In a more sophisticated version, we could extract specific details
            if len(text) > 20:
                return text
        except Exception:
            pass
        
        return None
    
    def _calculate_confidence(self, parsed: ParsedMeetingRequest) -> float:
        """Calculate confidence score for the parsing"""
        try:
            confidence = 0.0
            
            # Base confidence for having any content
            if parsed.original_text:
                confidence += 0.1
            
            # Boost for each component found
            if parsed.participant_names or parsed.participant_emails:
                confidence += 0.3
            if parsed.date_mentioned:
                confidence += 0.2
            if parsed.time_mentioned:
                confidence += 0.2
            if parsed.duration_mentioned:
                confidence += 0.1
            if parsed.title:
                confidence += 0.1
            
            # Boost for meeting-related keywords
            text_lower = parsed.original_text.lower()
            meeting_words_found = sum(1 for keyword in self.meeting_keywords if keyword in text_lower)
            confidence += min(meeting_words_found * 0.05, 0.15)
            
            # Cap at 1.0
            return min(confidence, 1.0)
        except Exception:
            return 0.1  # Minimal confidence if calculation fails

# Global instance
nlp_service = NLPService()
