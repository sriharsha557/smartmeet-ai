"""
Chat Interface with full PRD implementation:
- Natural language parsing with LLM
- Participant disambiguation 
- Availability checking against Google Sheets
- Alternative time slot suggestions
- Auto-generated meeting titles
- Meeting confirmation and scheduling
"""

import streamlit as st
from datetime import datetime, date, timedelta, time
from typing import List, Optional, Dict, Any
from models import Meeting, Participant, ParsedMeetingRequest, ParticipantMatch

# Initialize session state at module level
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if 'current_meeting_draft' not in st.session_state:
    st.session_state.current_meeting_draft = None
if 'participant_confirmations' not in st.session_state:
    st.session_state.participant_confirmations = {}
if 'suggested_time_slots' not in st.session_state:
    st.session_state.suggested_time_slots = []

# Import services
try:
    from services.nlp_service import nlp_service
except ImportError:
    from services.nlp_service_simple import simple_nlp_service as nlp_service

from services.participant_service import participant_service

try:
    from services.sheets_service import sheets_service
    USE_SHEETS = sheets_service.is_connected()
except:
    USE_SHEETS = False


def safe_rerun():
    """Safe rerun that works with different Streamlit versions"""
    try:
        st.rerun()
    except AttributeError:
        try:
            st.experimental_rerun()
        except AttributeError:
            if 'refresh_counter' not in st.session_state:
                st.session_state.refresh_counter = 0
            st.session_state.refresh_counter += 1


class ChatInterface:
    """Natural language chat interface for meeting scheduling"""
    
    def __init__(self):
        # Ensure session state variables are initialized
        if 'chat_history' not in st.session_state:
            st.session_state.chat_history = []
        if 'current_meeting_draft' not in st.session_state:
            st.session_state.current_meeting_draft = None
        if 'participant_confirmations' not in st.session_state:
            st.session_state.participant_confirmations = {}
        if 'suggested_time_slots' not in st.session_state:
            st.session_state.suggested_time_slots = []
    
    def render(self):
        """Render the chat interface"""
        st.subheader("💬 Smart Meeting Assistant")
        st.write("*Tell me about the meeting you'd like to schedule in natural language*")
        
        # Show connection status
        if USE_SHEETS:
            st.success("✓ Connected to Google Sheets")
        else:
            st.info("ℹ️ Using mock data (Google Sheets not connected)")
        
        # Chat history display
        self._display_chat_history()
        
        # Input area
        with st.container():
            user_input = st.text_area(
                "Type your meeting request:",
                placeholder="e.g., 'Schedule a meeting with John and Sarah tomorrow at 2pm for 1 hour'",
                height=100,
                key="chat_input"
            )
            
            col1, col2 = st.columns([1, 4])
            with col1:
                if st.button("💬 Send", type="primary"):
                    if user_input.strip():
                        self._process_user_input(user_input.strip())
                        # Clear input after processing
                        st.session_state.chat_input = ""
                        safe_rerun()
            
            with col2:
                if st.button("🗑️ Clear Chat"):
                    self._clear_chat()
                    safe_rerun()
        
        # Show current meeting draft if available
        if st.session_state.get('current_meeting_draft'):
            self._display_meeting_draft()
    
    def _display_chat_history(self):
        """Display chat history"""
        if 'chat_history' not in st.session_state:
            st.session_state.chat_history = []
            
        if not st.session_state.chat_history:
            st.info("👋 Hi! I'm your meeting assistant. Tell me about a meeting you'd like to schedule.")
            return
        
        chat_container = st.container()
        with chat_container:
            for i, message in enumerate(st.session_state.chat_history):
                if message['type'] == 'user':
                    with st.chat_message("user"):
                        st.write(message['content'])
                else:
                    with st.chat_message("assistant"):
                        st.write(message['content'])
                        if message.get('data'):
                            self._render_message_data(message['data'])
    
    def _render_message_data(self, data: Dict[str, Any]):
        """Render additional data in chat messages"""
        if data.get('type') == 'participant_matches':
            self._render_participant_matches(data['matches'])
        elif data.get('type') == 'meeting_summary':
            self._render_meeting_summary(data['meeting'])
        elif data.get('type') == 'time_slot_suggestions':
            self._render_time_slot_suggestions(data['slots'], data.get('conflict_info'))
        elif data.get('type') == 'meeting_confirmation':
            self._render_confirmation_buttons()
    
    def _render_meeting_summary(self, meeting: Meeting):
        """Render meeting summary in chat"""
        with st.container():
            st.markdown("**📋 Meeting Summary:**")
            
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**Title:** {meeting.title}")
                if meeting.description:
                    st.write(f"**Description:** {meeting.description}")
                if meeting.start_time:
                    st.write(f"**Date:** {meeting.start_time.strftime('%A, %B %d, %Y')}")
                    st.write(f"**Time:** {meeting.start_time.strftime('%I:%M %p')}")
                st.write(f"**Duration:** {meeting.duration_minutes} minutes")
                st.write(f"**Priority:** {meeting.priority.title()}")
            
            with col2:
                st.write("**Participants:**")
                for participant in meeting.participants:
                    st.write(f"  • {participant.name}")
                    st.write(f"    _{participant.email}_")
    
    def _render_time_slot_suggestions(self, slots: List[Dict], conflict_info: Dict = None):
        """Render alternative time slot suggestions (PRD requirement)"""
        if conflict_info:
            st.warning(f"⚠️ **Conflict detected:** {conflict_info.get('message', 'Some participants are unavailable')}")
            st.write("**Suggested alternative time slots:**")
        else:
            st.write("**Available time slots:**")
        
        for i, slot in enumerate(slots[:5]):  # Show top 5
            slot_date = slot['date']
            start_time = slot['start_time']
            end_time = slot['end_time']
            
            # Format display
            date_str = slot_date.strftime('%A, %B %d')
            time_str = f"{start_time.strftime('%I:%M %p')} - {end_time.strftime('%I:%M %p')}"
            
            col1, col2 = st.columns([3, 1])
            with col1:
                st.write(f"**Option {i+1}:** {date_str} at {time_str}")
            with col2:
                if st.button("Select", key=f"select_slot_{i}_{slot_date}_{start_time}"):
                    self._select_time_slot(slot)
                    safe_rerun()
    
    def _render_confirmation_buttons(self):
        """Render final confirmation buttons"""
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("✅ Confirm & Schedule", key="confirm_meeting", type="primary"):
                self._schedule_meeting()
                safe_rerun()
        with col2:
            if st.button("🔄 Change Time", key="change_time"):
                self._request_time_change()
                safe_rerun()
        with col3:
            if st.button("❌ Cancel", key="cancel_meeting"):
                self._cancel_draft()
                safe_rerun()
    
    def _process_user_input(self, user_input: str):
        """Process user input and generate response"""
        self._add_chat_message('user', user_input)
        
        if nlp_service is None:
            self._add_chat_message(
                'assistant',
                "Sorry, the NLP service is not available. Please check the installation."
            )
            return
        
        # Parse the input using LLM
        parsed = nlp_service.parse_meeting_request(user_input)
        
        if parsed.confidence < 0.3:
            self._add_chat_message(
                'assistant',
                "I'm not sure I understood that. Could you please rephrase? "
                "For example: 'Schedule a meeting with John and Sarah tomorrow at 2pm'"
            )
            return
        
        # Check if this is a follow-up
        if st.session_state.get('current_meeting_draft') and self._is_followup_message(user_input):
            self._handle_followup_message(user_input, parsed)
        else:
            self._handle_new_meeting_request(parsed)
    
    def _is_followup_message(self, message: str) -> bool:
        """Check if message is a follow-up"""
        followup_indicators = ['yes', 'no', 'correct', 'wrong', 'change', 'modify', 'update']
        message_lower = message.lower()
        return any(indicator in message_lower for indicator in followup_indicators)
    
    def _handle_new_meeting_request(self, parsed: ParsedMeetingRequest):
        """Handle a new meeting request (PRD workflow)"""
        # Step 1: Resolve participants
        participant_matches = participant_service.resolve_participants(
            parsed.participant_names, 
            parsed.participant_emails
        )
        
        # Step 2: Check if we need participant confirmation (PRD requirement)
        needs_confirmation = any(
            not match.is_exact or len(match.matches) > 1 
            for match in participant_matches
        )
        
        if needs_confirmation:
            self._request_participant_confirmation(participant_matches, parsed)
        else:
            # All participants confirmed, proceed to availability check
            participants = []
            for match in participant_matches:
                if match.matches:
                    participants.append(match.matches[0])
            
            self._check_availability_and_suggest(participants, parsed)
    
    def _request_participant_confirmation(
        self, 
        matches: List[ParticipantMatch], 
        parsed: ParsedMeetingRequest
    ):
        """Request confirmation for participant matches (PRD requirement)"""
        st.session_state.pending_parsed_request = parsed
        
        message = "I found some participants, but I need your confirmation:"
        
        data = {
            'type': 'participant_matches',
            'matches': matches,
            'parsed': parsed
        }
        
        self._add_chat_message('assistant', message, data)
    
    def _render_participant_matches(self, matches: List[ParticipantMatch]):
        """Render participant matches for confirmation"""
        for i, match in enumerate(matches):
            already_confirmed = match.query in st.session_state.get('participant_confirmations', {})
            
            if already_confirmed:
                confirmed_participant = st.session_state.participant_confirmations[match.query]
                st.success(f"✅ {match.query} → {confirmed_participant.name} ({confirmed_participant.email})")
                continue
            
            with st.expander(f"'{match.query}' - {len(match.matches)} match(es) found", expanded=True):
                if len(match.matches) == 0:
                    st.warning("No matches found. Would you like to add this as an external participant?")
                    if st.button(f"Add '{match.query}' as external", key=f"add_external_{i}_{match.query}"):
                        self._add_external_participant(match.query)
                elif len(match.matches) == 1:
                    participant = match.matches[0]
                    self._render_participant_option(participant, i, match.query, single=True)
                else:
                    st.write("Multiple matches found. Please select:")
                    for j, participant in enumerate(match.matches[:5]):
                        self._render_participant_option(participant, f"{i}_{j}", match.query)
    
    def _render_participant_option(self, participant: Participant, key_id: Any, query: str, single: bool = False):
        """Render a single participant option"""
        col1, col2, col3 = st.columns([2, 2, 1])
        with col1:
            st.write(f"**{participant.name}**")
            st.write(participant.email)
        with col2:
            if participant.department:
                st.write(f"*{participant.department}*")
            if participant.title:
                st.write(f"*{participant.title}*")
        with col3:
            button_label = "✅ Confirm" if single else "Select"
            if st.button(button_label, key=f"select_{key_id}_{participant.email}_{hash(query)}"):
                self._confirm_participant(query, participant)
    
    def _confirm_participant(self, query: str, participant: Participant):
        """Confirm a participant selection"""
        if 'participant_confirmations' not in st.session_state:
            st.session_state.participant_confirmations = {}
        
        st.session_state.participant_confirmations[query] = participant
        
        self._add_chat_message(
            'assistant',
            f"✅ Confirmed: {participant.name} ({participant.email})"
        )
        
        # Check if all participants are confirmed
        parsed = st.session_state.get('pending_parsed_request')
        if parsed:
            all_queries = parsed.participant_names + parsed.participant_emails
            confirmed_queries = list(st.session_state.participant_confirmations.keys())
            
            if all(query in confirmed_queries for query in all_queries):
                # All confirmed, proceed to availability check
                confirmed_participants = list(st.session_state.participant_confirmations.values())
                self._check_availability_and_suggest(confirmed_participants, parsed)
                
                # Clear temporary state
                if 'pending_parsed_request' in st.session_state:
                    del st.session_state.pending_parsed_request
                st.session_state.participant_confirmations = {}
        
        safe_rerun()
    
    def _add_external_participant(self, query: str):
        """Add external participant"""
        try:
            if '@' in query:
                participant = participant_service.add_external_participant(query)
                self._confirm_participant(query, participant)
            else:
                st.info(f"To add '{query}' as an external participant, please provide their email address.")
                self._add_chat_message(
                    'assistant',
                    f"I need an email address to add '{query}'. Please provide their email."
                )
        except ValueError as e:
            st.error(str(e))
    
    def _check_availability_and_suggest(
        self, 
        participants: List[Participant], 
        parsed: ParsedMeetingRequest
    ):
        """Check availability and suggest time slots (PRD requirement)"""
        self._add_chat_message(
            'assistant',
            f"Great! Now checking availability for {len(participants)} participants..."
        )
        
        # Determine target date and time
        target_date = parsed.date_mentioned or (date.today() + timedelta(days=1))
        
        # Parse time if provided
        requested_time = None
        if parsed.time_mentioned:
            requested_time = self._parse_time_string(parsed.time_mentioned)
        
        # Parse duration
        duration_minutes = self._parse_duration(parsed.duration_mentioned) or 60
        
        # Check if requested slot is available
        if requested_time:
            end_time = (
                datetime.combine(target_date, requested_time) + 
                timedelta(minutes=duration_minutes)
            ).time()
            
            availability = participant_service.get_availability_summary(
                participants, target_date, requested_time, end_time
            )
            
            conflicts = [name for email, status in availability.items() 
                        if status == 'busy' 
                        for p in participants if p.email == email 
                        for name in [p.name]]
            
            if conflicts:
                # Requested time has conflicts - suggest alternatives (PRD requirement)
                self._add_chat_message(
                    'assistant',
                    f"⚠️ Unfortunately, {', '.join(conflicts)} {'is' if len(conflicts) == 1 else 'are'} busy at that time."
                )
                
                # Find alternative slots
                alternative_slots = participant_service.suggest_alternative_slots(
                    participants, target_date, requested_time, duration_minutes, days_to_check=2
                )
                
                if alternative_slots:
                    st.session_state.suggested_time_slots = alternative_slots
                    st.session_state.pending_meeting_info = {
                        'participants': participants,
                        'parsed': parsed,
                        'duration_minutes': duration_minutes
                    }
                    
                    conflict_info = {
                        'message': f"{', '.join(conflicts)} unavailable at requested time"
                    }
                    
                    self._add_chat_message(
                        'assistant',
                        "Here are some alternative time slots when everyone is available:",
                        {
                            'type': 'time_slot_suggestions',
                            'slots': alternative_slots,
                            'conflict_info': conflict_info
                        }
                    )
                else:
                    self._add_chat_message(
                        'assistant',
                        "I couldn't find any suitable alternative slots. Would you like to try a different date?"
                    )
            else:
                # Requested time is available - create meeting
                self._add_chat_message(
                    'assistant',
                    f"🎉 Great news! All participants are available at {requested_time.strftime('%I:%M %p')}."
                )
                self._create_meeting_draft(participants, parsed, target_date, requested_time, duration_minutes)
        else:
            # No specific time requested - suggest available slots
            available_slots = participant_service.find_available_time_slots(
                participants, target_date, duration_minutes
            )
            
            if available_slots:
                st.session_state.suggested_time_slots = available_slots
                st.session_state.pending_meeting_info = {
                    'participants': participants,
                    'parsed': parsed,
                    'duration_minutes': duration_minutes
                }
                
                self._add_chat_message(
                    'assistant',
                    "Here are some available time slots:",
                    {
                        'type': 'time_slot_suggestions',
                        'slots': available_slots
                    }
                )
            else:
                self._add_chat_message(
                    'assistant',
                    "I couldn't find any available slots. Would you like to try a different date?"
                )
    
    def _select_time_slot(self, slot: Dict):
        """User selected a time slot from suggestions"""
        pending_info = st.session_state.get('pending_meeting_info')
        if not pending_info:
            return
        
        participants = pending_info['participants']
        parsed = pending_info['parsed']
        duration_minutes = pending_info['duration_minutes']
        
        selected_date = slot['date']
        selected_time = slot['start_time']
        
        self._add_chat_message(
            'assistant',
            f"✅ Selected: {selected_date.strftime('%A, %B %d')} at {selected_time.strftime('%I:%M %p')}"
        )
        
        self._create_meeting_draft(
            participants, parsed, selected_date, selected_time, duration_minutes
        )
    
    def _create_meeting_draft(
        self,
        participants: List[Participant],
        parsed: ParsedMeetingRequest,
        meeting_date: date,
        meeting_time: time,
        duration_minutes: int
    ):
        """Create meeting draft with all details"""
        meeting = Meeting()
        
        # Auto-generate title if not provided (PRD requirement)
        if parsed.title:
            meeting.title = parsed.title
        else:
            meeting.title = self._generate_meeting_title(participants, parsed)
        
        meeting.description = parsed.description or f"Meeting with {', '.join([p.name for p in participants])}"
        meeting.participants = participants
        meeting.start_time = datetime.combine(meeting_date, meeting_time)
        meeting.duration_minutes = duration_minutes
        meeting.end_time = meeting.start_time + timedelta(minutes=duration_minutes)
        meeting.priority = parsed.priority_mentioned or "medium"
        meeting.status = "draft"
        
        st.session_state.current_meeting_draft = meeting
        
        # Show meeting summary for final confirmation
        self._add_chat_message(
            'assistant',
            "📋 **Meeting Details Summary:**\n\nPlease review the meeting details below:",
            {
                'type': 'meeting_summary',
                'meeting': meeting
            }
        )
        
        self._add_chat_message(
            'assistant', 
            "What would you like to do?",
            {
                'type': 'meeting_confirmation'
            }
        )
    
    def _generate_meeting_title(
        self, 
        participants: List[Participant], 
        parsed: ParsedMeetingRequest
    ) -> str:
        """
        Auto-generate meeting title (PRD requirement)
        Template: "Meeting with [Participants]"
        """
        if len(participants) == 0:
            return "New Meeting"
        elif len(participants) == 1:
            return f"Meeting with {participants[0].name}"
        elif len(participants) == 2:
            return f"Meeting with {participants[0].name} and {participants[1].name}"
        elif len(participants) <= 4:
            names = ", ".join([p.name for p in participants[:-1]])
            return f"Meeting with {names}, and {participants[-1].name}"
        else:
            return f"Team Meeting ({len(participants)} participants)"
    
    def _parse_time_string(self, time_str: str) -> Optional[time]:
        """Parse time string to time object"""
        if not time_str:
            return None
        
        try:
            # Try 24-hour format first (HH:MM)
            if ':' in time_str and ('AM' not in time_str.upper() and 'PM' not in time_str.upper()):
                return datetime.strptime(time_str, "%H:%M").time()
            
            # Try 12-hour with minutes (HH:MM AM/PM)
            if ':' in time_str:
                return datetime.strptime(time_str, "%I:%M %p").time()
            else:
                # Try without minutes (HH AM/PM)
                return datetime.strptime(time_str, "%I %p").time()
        except ValueError:
            return None
    
    def _parse_duration(self, duration_str: Optional[str]) -> Optional[int]:
        """Parse duration string to minutes"""
        if not duration_str:
            return None
        
        duration_map = {
            "15 minutes": 15,
            "30 minutes": 30,
            "45 minutes": 45,
            "1 hour": 60,
            "1.5 hours": 90,
            "2 hours": 120,
            "2.5 hours": 150,
            "3 hours": 180
        }
        
        return duration_map.get(duration_str)
    
    def _display_meeting_draft(self):
        """Display current meeting draft"""
        st.markdown("---")
        st.subheader("📝 Meeting Draft")
        
        meeting = st.session_state.current_meeting_draft
        
        col1, col2 = st.columns([3, 1])
        with col1:
            st.write(f"**Title:** {meeting.title}")
            if meeting.description:
                st.write(f"**Description:** {meeting.description}")
            
            if meeting.start_time:
                st.write(f"**Date & Time:** {meeting.start_time.strftime('%A, %B %d, %Y at %I:%M %p')}")
                st.write(f"**Duration:** {meeting.duration_minutes} minutes")
            
            st.write(f"**Participants:**")
            for participant in meeting.participants:
                st.write(f"  • {participant.name} ({participant.email})")
            
            st.write(f"**Priority:** {meeting.priority.title()}")
        
        with col2:
            if st.button("📅 Schedule Now", type="primary", key="schedule_now_btn"):
                self._schedule_meeting()
            if st.button("🔄 Change Time", key="change_time_btn"):
                self._request_time_change()
            if st.button("🗑️ Cancel", key="cancel_draft_btn"):
                self._cancel_draft()
    
    def _schedule_meeting(self):
        """Schedule the meeting - save to Google Sheets (PRD requirement)"""
        meeting = st.session_state.current_meeting_draft
        meeting.status = "scheduled"
        meeting.id = f"MTG_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        meeting.updated_at = datetime.now()
        
        # Save to Google Sheets (PRD Phase 1 requirement)
        success = False
        if USE_SHEETS:
            success = sheets_service.save_meeting(meeting)
            if success:
                storage_msg = "Meeting saved to Google Sheets ✓"
            else:
                storage_msg = "⚠️ Failed to save to Google Sheets, but meeting is confirmed"
        else:
            # Fallback to mock data
            from utils.mock_data import mock_data
            mock_data.add_meeting(meeting)
            storage_msg = "Meeting saved to mock data ✓"
            success = True
        
        if success:
            self._add_chat_message(
                'assistant',
                f"🎉 Perfect! Your meeting '{meeting.title}' is scheduled for "
                f"{meeting.start_time.strftime('%A, %B %d at %I:%M %p')}.\n\n"
                f"📧 Calendar invitations will be sent to all {len(meeting.participants)} participants.\n\n"
                f"{storage_msg}"
            )
            
            # Clear the draft
            st.session_state.current_meeting_draft = None
            st.session_state.suggested_time_slots = []
            if 'pending_meeting_info' in st.session_state:
                del st.session_state.pending_meeting_info
            
            st.success("Meeting scheduled successfully!")
            st.balloons()
        else:
            self._add_chat_message(
                'assistant',
                "❌ Sorry, there was an error scheduling the meeting. Please try again."
            )
    
    def _request_time_change(self):
        """Request to change the meeting time"""
        meeting = st.session_state.current_meeting_draft
        
        self._add_chat_message(
            'assistant',
            "I can help you find a different time. Let me suggest some alternatives..."
        )
        
        # Find alternative slots
        alternative_slots = participant_service.suggest_alternative_slots(
            meeting.participants,
            meeting.start_time.date(),
            meeting.start_time.time(),
            meeting.duration_minutes,
            days_to_check=3
        )
        
        if alternative_slots:
            st.session_state.suggested_time_slots = alternative_slots
            st.session_state.pending_meeting_info = {
                'participants': meeting.participants,
                'parsed': ParsedMeetingRequest(
                    original_text="",
                    title=meeting.title,
                    description=meeting.description,
                    priority_mentioned=meeting.priority
                ),
                'duration_minutes': meeting.duration_minutes
            }
            
            self._add_chat_message(
                'assistant',
                "Here are some alternative time slots:",
                {
                    'type': 'time_slot_suggestions',
                    'slots': alternative_slots
                }
            )
    
    def _cancel_draft(self):
        """Cancel meeting draft"""
        st.session_state.current_meeting_draft = None
        st.session_state.suggested_time_slots = []
        if 'pending_meeting_info' in st.session_state:
            del st.session_state.pending_meeting_info
        
        self._add_chat_message(
            'assistant', 
            "Meeting draft cancelled. How else can I help you?"
        )
        safe_rerun()
    
    def _handle_followup_message(self, user_input: str, parsed: ParsedMeetingRequest):
        """Handle follow-up messages to modify existing draft"""
        self._add_chat_message(
            'assistant', 
            "I understand you want to modify the meeting. You can say things like:\n"
            "- 'Change the time to 3pm'\n"
            "- 'Add Maria to the meeting'\n"
            "- 'Make it 2 hours instead'\n"
            "- 'Change the title to Project Review'"
        )
    
    def _add_chat_message(self, type: str, content: str, data: Dict[str, Any] = None):
        """Add message to chat history"""
        if 'chat_history' not in st.session_state:
            st.session_state.chat_history = []
            
        message = {
            'type': type,
            'content': content,
            'timestamp': datetime.now(),
            'data': data
        }
        st.session_state.chat_history.append(message)
    
    def _clear_chat(self):
        """Clear chat history"""
        st.session_state.chat_history = []
        st.session_state.current_meeting_draft = None
        st.session_state.participant_confirmations = {}
        st.session_state.suggested_time_slots = []
        if 'pending_parsed_request' in st.session_state:
            del st.session_state.pending_parsed_request
        if 'pending_meeting_info' in st.session_state:
            del st.session_state.pending_meeting_info


# Global instance
chat_interface = ChatInterface()
