import streamlit as st
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from models import Meeting, Participant, ParsedMeetingRequest, ParticipantMatch

# Try to import NLP service, fallback to simple version
try:
    from services.nlp_service import nlp_service
except ImportError:
    try:
        from services.nlp_service_simple import simple_nlp_service as nlp_service
    except ImportError:
        nlp_service = None

from services.participant_service import participant_service

class ChatInterface:
    """Natural language chat interface for meeting scheduling"""
    
    def __init__(self):
        if 'chat_history' not in st.session_state:
            st.session_state.chat_history = []
        if 'current_meeting_draft' not in st.session_state:
            st.session_state.current_meeting_draft = None
        if 'participant_confirmations' not in st.session_state:
            st.session_state.participant_confirmations = {}
    
    def render(self):
        """Render the chat interface"""
        st.subheader("💬 Smart Meeting Assistant")
        st.write("*Tell me about the meeting you'd like to schedule in natural language*")
        
        # Chat history display
        self._display_chat_history()
        
        # Input area
        with st.container():
            user_input = st.text_area(
                "Type your meeting request:",
                placeholder="e.g., 'Schedule a team meeting with John and Sarah tomorrow at 2pm for 1 hour'",
                height=100,
                key="chat_input"
            )
            
            col1, col2 = st.columns([1, 4])
            with col1:
                if st.button("💬 Send", type="primary"):
                    if user_input.strip():
                        self._process_user_input(user_input.strip())
                        st.rerun()
            
            with col2:
                if st.button("🗑️ Clear Chat"):
                    self._clear_chat()
                    st.rerun()
        
        # Show current meeting draft if available
        if st.session_state.current_meeting_draft:
            self._display_meeting_draft()
    
    def _display_chat_history(self):
        """Display chat history"""
        if not st.session_state.chat_history:
            st.info("👋 Hi! I'm your meeting assistant. Tell me about a meeting you'd like to schedule.")
            return
        
        # Create a container for chat history
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
        elif data.get('type') == 'confirmation_needed'):
            self._render_confirmation_options(data)
    
    def _process_user_input(self, user_input: str):
        """Process user input and generate response"""
        # Add user message to history
        self._add_chat_message('user', user_input)
        
        # Check if NLP service is available
        if nlp_service is None:
            self._add_chat_message(
                'assistant',
                "Sorry, the NLP service is not available. Please check the installation."
            )
            return
        
        # Parse the input
        parsed = nlp_service.parse_meeting_request(user_input)
        
        if parsed.confidence < 0.3:
            self._add_chat_message(
                'assistant',
                "I'm not sure I understood that. Could you please rephrase? For example, you could say: 'Schedule a meeting with John and Sarah tomorrow at 2pm'"
            )
            return
        
        # Check if this is a follow-up to an existing draft
        if st.session_state.current_meeting_draft and self._is_followup_message(user_input):
            self._handle_followup_message(user_input, parsed)
        else:
            self._handle_new_meeting_request(parsed)
    
    def _is_followup_message(self, message: str) -> bool:
        """Check if message is a follow-up to existing conversation"""
        followup_indicators = ['yes', 'no', 'correct', 'wrong', 'that\'s right', 'not quite', 'actually']
        message_lower = message.lower()
        return any(indicator in message_lower for indicator in followup_indicators)
    
    def _handle_new_meeting_request(self, parsed: ParsedMeetingRequest):
        """Handle a new meeting request"""
        # Resolve participants
        participant_matches = participant_service.resolve_participants(
            parsed.participant_names, 
            parsed.participant_emails
        )
        
        # Check if we need participant confirmation
        needs_confirmation = any(
            not match.is_exact or len(match.matches) > 1 
            for match in participant_matches
        )
        
        if needs_confirmation:
            self._request_participant_confirmation(participant_matches, parsed)
        else:
            # Create meeting draft
            self._create_meeting_draft(participant_matches, parsed)
    
    def _request_participant_confirmation(self, matches: List[ParticipantMatch], parsed: ParsedMeetingRequest):
        """Request confirmation for participant matches"""
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
            with st.expander(f"'{match.query}' - {len(match.matches)} match(es) found", expanded=True):
                if len(match.matches) == 0:
                    st.warning("No matches found. Would you like to add this as an external participant?")
                    if st.button(f"Add '{match.query}' as external", key=f"add_external_{i}"):
                        self._add_external_participant(match.query)
                elif len(match.matches) == 1:
                    participant = match.matches[0]
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
                        if st.button("✅ Confirm", key=f"confirm_{i}"):
                            self._confirm_participant(match.query, participant)
                else:
                    st.write("Multiple matches found. Please select:")
                    for j, participant in enumerate(match.matches[:5]):  # Limit to top 5
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
                            if st.button("Select", key=f"select_{i}_{j}"):
                                self._confirm_participant(match.query, participant)
    
    def _confirm_participant(self, query: str, participant: Participant):
        """Confirm a participant selection"""
        if 'participant_confirmations' not in st.session_state:
            st.session_state.participant_confirmations = {}
        
        st.session_state.participant_confirmations[query] = participant
        
        # Check if all participants are confirmed
        parsed = st.session_state.get('pending_parsed_request')
        if parsed:
            all_queries = parsed.participant_names + parsed.participant_emails
            confirmed_queries = list(st.session_state.participant_confirmations.keys())
            
            if all(query in confirmed_queries for query in all_queries):
                # All confirmed, create meeting draft
                confirmed_participants = list(st.session_state.participant_confirmations.values())
                self._create_meeting_draft_with_participants(confirmed_participants, parsed)
                
                # Clear temporary state
                del st.session_state.pending_parsed_request
                st.session_state.participant_confirmations = {}
                st.rerun()
    
    def _add_external_participant(self, query: str):
        """Add external participant"""
        try:
            if '@' in query:
                participant = participant_service.add_external_participant(query)
            else:
                # Ask for email
                email = st.text_input(f"Enter email for {query}:", key=f"email_{query}")
                if email:
                    participant = participant_service.add_external_participant(email, query)
                else:
                    return
            
            self._confirm_participant(query, participant)
        except ValueError as e:
            st.error(str(e))
    
    def _create_meeting_draft_with_participants(self, participants: List[Participant], parsed: ParsedMeetingRequest):
        """Create meeting draft with confirmed participants"""
        # Create the meeting object
        meeting = Meeting()
        meeting.title = parsed.title or "New Meeting"
        meeting.description = parsed.description
        meeting.participants = participants
        
        # Set date and time
        if parsed.date_mentioned:
            if parsed.time_mentioned:
                time_str = parsed.time_mentioned
                # Parse time (simplified)
                try:
                    if 'AM' in time_str or 'PM' in time_str:
                        time_obj = datetime.strptime(time_str, "%I:%M %p").time()
                    else:
                        time_obj = datetime.strptime(time_str, "%H:%M").time()
                    
                    meeting.start_time = datetime.combine(parsed.date_mentioned, time_obj)
                except:
                    # Fallback to default time
                    meeting.start_time = datetime.combine(parsed.date_mentioned, datetime.min.time().replace(hour=14))
            else:
                # Default to 2 PM
                meeting.start_time = datetime.combine(parsed.date_mentioned, datetime.min.time().replace(hour=14))
        
        # Set duration
        if parsed.duration_mentioned:
            duration_map = {
                "30 minutes": 30, "45 minutes": 45, "1 hour": 60,
                "1.5 hours": 90, "2 hours": 120, "2.5 hours": 150, "3 hours": 180
            }
            meeting.duration_minutes = duration_map.get(parsed.duration_mentioned, 60)
        else:
            meeting.duration_minutes = 60
        
        if meeting.start_time:
            meeting.end_time = meeting.start_time + timedelta(minutes=meeting.duration_minutes)
        
        # Set priority
        if parsed.priority_mentioned:
            meeting.priority = parsed.priority_mentioned
        
        meeting.status = "draft"
        st.session_state.current_meeting_draft = meeting
        
        # Add success message
        self._add_chat_message(
            'assistant',
            f"Great! I've created a meeting draft with {len(participants)} participant(s). Please review the details below and let me know if you'd like to make any changes.",
            {
                'type': 'meeting_summary',
                'meeting': meeting
            }
        )
    
    def _create_meeting_draft(self, matches: List[ParticipantMatch], parsed: ParsedMeetingRequest):
        """Create meeting draft from exact matches"""
        participants = []
        for match in matches:
            if match.matches:
                participants.extend(match.matches)
        
        self._create_meeting_draft_with_participants(participants, parsed)
    
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
            if st.button("📅 Schedule Meeting", type="primary"):
                self._schedule_meeting()
            if st.button("✏️ Edit Details"):
                self._edit_meeting_draft()
            if st.button("🗑️ Cancel Draft"):
                self._cancel_draft()
    
    def _schedule_meeting(self):
        """Schedule the meeting"""
        meeting = st.session_state.current_meeting_draft
        meeting.status = "scheduled"
        meeting.id = f"meeting_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # In a real implementation, this would save to database and send invitations
        self._add_chat_message(
            'assistant',
            f"🎉 Perfect! I've scheduled your meeting '{meeting.title}' for {meeting.start_time.strftime('%A, %B %d at %I:%M %p')}. Invitations will be sent to all participants."
        )
        
        # Clear the draft
        st.session_state.current_meeting_draft = None
        st.success("Meeting scheduled successfully!")
        st.balloons()
    
    def _edit_meeting_draft(self):
        """Edit meeting draft"""
        self._add_chat_message(
            'assistant',
            "What would you like to change about the meeting? You can say things like 'change the time to 3pm' or 'add Maria to the meeting'."
        )
    
    def _cancel_draft(self):
        """Cancel meeting draft"""
        st.session_state.current_meeting_draft = None
        self._add_chat_message('assistant', "Meeting draft cancelled. How else can I help you?")
        st.rerun()
    
    def _handle_followup_message(self, user_input: str, parsed: ParsedMeetingRequest):
        """Handle follow-up messages to modify existing draft"""
        # This would handle modifications to existing meeting
        self._add_chat_message('assistant', "Meeting modification is not implemented yet. Please create a new meeting.")
    
    def _add_chat_message(self, type: str, content: str, data: Dict[str, Any] = None):
        """Add message to chat history"""
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
        if 'pending_parsed_request' in st.session_state:
            del st.session_state.pending_parsed_request

# Global instance
chat_interface = ChatInterface()
