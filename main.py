"""
SmartMeet MVP - Main Application
Aligned with PRD specifications
"""

import streamlit as st
import os
import sys
from datetime import datetime, timedelta, date
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Add current directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Page configuration
st.set_page_config(
    page_title="SmartMeet AI",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Import our components
try:
    from components.chat_interface import chat_interface
    from models import Meeting, Participant
    
    # Try to import services
    try:
        from services.nlp_service import nlp_service
        NLP_SERVICE_TYPE = "llm"
    except ImportError:
        try:
            from services.nlp_service_simple import simple_nlp_service as nlp_service
            NLP_SERVICE_TYPE = "simple"
        except ImportError:
            nlp_service = None
            NLP_SERVICE_TYPE = "none"
    
    # Try to import data source (Sheets or Mock)
    try:
        from services.sheets_service import sheets_service
        if sheets_service.is_connected():
            DATA_SOURCE = "sheets"
            data_service = sheets_service
        else:
            from utils.mock_data import mock_data
            DATA_SOURCE = "mock"
            data_service = mock_data
    except Exception as e:
        from utils.mock_data import mock_data
        DATA_SOURCE = "mock"
        data_service = mock_data
        
except ImportError as e:
    st.error(f"❌ Error importing modules: {e}")
    st.info("Please ensure all required files are present and dependencies are installed.")
    st.code("pip install -r requirements.txt")
    st.stop()


# Compatibility fix for different Streamlit versions
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


def initialize_session_state():
    """Initialize all required session state variables"""
    defaults = {
        'app_initialized': False,
        'chat_history': [],
        'current_meeting_draft': None,
        'participant_confirmations': {},
        'suggested_time_slots': [],
    }
    
    for key, default_value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default_value


def get_meetings() -> list:
    """Get meetings from data source"""
    try:
        if DATA_SOURCE == "sheets":
            return data_service.get_all_meetings()
        else:
            return data_service.get_meetings()
    except Exception as e:
        st.error(f"Error loading meetings: {e}")
        return []


def get_participants() -> list:
    """Get participants from data source"""
    try:
        if DATA_SOURCE == "sheets":
            return data_service.get_all_participants()
        else:
            return data_service.get_participants()
    except Exception as e:
        st.error(f"Error loading participants: {e}")
        return []


# Header
st.markdown("""
<div style="text-align: center; margin-bottom: 2rem;">
    <h1 style="color: #1f77b4; margin-bottom: 0;">🤖 SmartMeet AI</h1>
    <p style="color: #666; font-size: 1.2rem; margin-top: 0.5rem;">Intelligent Meeting Scheduling Assistant</p>
</div>
""", unsafe_allow_html=True)


def main():
    """Main application function"""
    
    # Initialize session state
    initialize_session_state()
    
    if not st.session_state.app_initialized:
        st.session_state.app_initialized = True
        # Load mock data on first run if using mock data
        if DATA_SOURCE == "mock":
            data_service.load_from_file()

    # Sidebar
    with st.sidebar:
        st.title("🎯 Navigation")
        
        # Show connection status
        if DATA_SOURCE == "sheets":
            st.success("✅ Connected to Google Sheets")
        else:
            st.info("💡 Using Mock Data (Demo Mode)")
        
        if NLP_SERVICE_TYPE == "llm":
            st.success("🧠 LLM NLP Active")
        elif NLP_SERVICE_TYPE == "simple":
            st.warning("🧠 Simple NLP (No API Key)")
        else:
            st.error("❌ NLP Service Unavailable")
        
        st.markdown("---")
        
        # Navigation menu
        page = st.selectbox(
            "Choose a page:",
            ["💬 Smart Chat", "🏠 Dashboard", "📅 Calendar View", "👥 Participants", "⚙️ Settings"]
        )
        
        st.markdown("---")
        
        # Quick stats
        st.markdown("### 📊 Quick Stats")
        try:
            meetings = get_meetings()
            participants = get_participants()
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Meetings", len(meetings))
            with col2:
                st.metric("People", len(participants))
        except Exception as e:
            st.warning("Stats unavailable")
        
        # Recent activity
        st.markdown("### 🕒 Recent")
        try:
            meetings = get_meetings()
            if meetings:
                recent_meetings = sorted(meetings, key=lambda m: m.created_at if m.created_at else datetime.now(), reverse=True)[:3]
                for meeting in recent_meetings:
                    with st.expander(f"{meeting.title[:20]}...", expanded=False):
                        st.write(f"**Participants:** {len(meeting.participants)}")
                        st.write(f"**Status:** {meeting.status.title()}")
                        if meeting.start_time:
                            st.write(f"**When:** {meeting.start_time.strftime('%m/%d %I:%M %p')}")
            else:
                st.info("No meetings yet")
        except Exception as e:
            st.warning("Recent activity unavailable")

    # Main content based on selected page
    if page == "💬 Smart Chat":
        show_chat_page()
    elif page == "🏠 Dashboard":
        show_dashboard()
    elif page == "📅 Calendar View":
        show_calendar_view()
    elif page == "👥 Participants":
        show_participants_page()
    elif page == "⚙️ Settings":
        show_settings_page()


def show_chat_page():
    """Show the smart chat interface"""
    st.header("💬 Smart Meeting Scheduler")
    
    # Instructions
    with st.expander("ℹ️ How to use", expanded=False):
        st.markdown("""
        **Examples of what you can say:**
        - "Schedule a meeting with John and Sarah tomorrow at 2pm"
        - "Set up a team sync with Mike, Emily and David next Monday for 1 hour"
        - "Book a client call with jennifer.lee@company.com on Friday at 10am"
        - "Create a high priority meeting with the engineering team for 2 hours"
        
        **I can understand:**
        - 👥 Participant names (I'll help you find the right people)
        - 📅 Dates (today, tomorrow, Monday, Jan 15, etc.)
        - 🕐 Times (2pm, 14:30, 10:00 AM, etc.)
        - ⏱️ Duration (30 minutes, 1 hour, 2.5 hours, etc.)
        - 🔥 Priority (urgent, high, normal, low)
        """)
    
    # Render the chat interface
    try:
        chat_interface.render()
    except Exception as e:
        st.error(f"Error rendering chat interface: {e}")
        st.info("Please check that all services are properly configured.")


def show_dashboard():
    """Show dashboard with meeting overview"""
    st.header("🏠 Dashboard")
    
    try:
        # Get data
        meetings = get_meetings()
        participants = get_participants()
        
        # Quick stats
        col1, col2, col3, col4 = st.columns(4)
        
        # Calculate stats
        today = datetime.now().date()
        today_meetings = [m for m in meetings if m.start_time and m.start_time.date() == today]
        this_week_start = today - timedelta(days=today.weekday())
        this_week_meetings = [m for m in meetings if m.start_time and m.start_time.date() >= this_week_start]
        scheduled_meetings = [m for m in meetings if m.status == "scheduled"]
        draft_meetings = [m for m in meetings if m.status == "draft"]
        
        with col1:
            st.metric("📅 Today", len(today_meetings), "meetings")
        
        with col2:
            st.metric("📊 This Week", len(this_week_meetings), "meetings")
        
        with col3:
            st.metric("✅ Scheduled", len(scheduled_meetings), "confirmed")
        
        with col4:
            st.metric("📝 Drafts", len(draft_meetings), "pending")

        st.markdown("---")
        
        # Charts
        col1, col2 = st.columns(2)
        
        with col1:
            # Meeting frequency over time
            if meetings:
                meeting_dates = [m.start_time.date() for m in meetings if m.start_time]
                if meeting_dates:
                    date_counts = {}
                    for dt in meeting_dates:
                        date_counts[dt] = date_counts.get(dt, 0) + 1
                    
                    df = pd.DataFrame(list(date_counts.items()), columns=['Date', 'Meetings'])
                    df = df.sort_values('Date')
                    
                    fig = px.line(df, x='Date', y='Meetings', 
                                 title='📈 Meeting Frequency Over Time',
                                 markers=True)
                    fig.update_layout(height=400)
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No meeting dates available for chart")
            else:
                st.info("No meetings to display")
        
        with col2:
            # Meeting duration distribution
            if meetings:
                durations = [m.duration_minutes for m in meetings if m.duration_minutes]
                if durations:
                    duration_labels = []
                    for d in durations:
                        if d <= 30:
                            duration_labels.append('30 min')
                        elif d <= 60:
                            duration_labels.append('1 hour')
                        elif d <= 90:
                            duration_labels.append('1.5 hours')
                        elif d <= 120:
                            duration_labels.append('2 hours')
                        else:
                            duration_labels.append('2+ hours')
                    
                    from collections import Counter
                    duration_counts = Counter(duration_labels)
                    
                    fig = px.pie(values=list(duration_counts.values()), 
                                names=list(duration_counts.keys()),
                                title='⏱️ Meeting Duration Distribution')
                    fig.update_layout(height=400)
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No duration data available")
            else:
                st.info("No meetings to display")
        
        # Recent meetings table
        st.subheader("📋 Recent Meetings")
        
        if meetings:
            recent_meetings = sorted(meetings, key=lambda m: m.created_at if m.created_at else datetime.now(), reverse=True)[:10]
            
            table_data = []
            for meeting in recent_meetings:
                table_data.append({
                    'Title': meeting.title,
                    'Participants': len(meeting.participants),
                    'Date': meeting.start_time.strftime('%m/%d/%Y') if meeting.start_time else 'TBD',
                    'Time': meeting.start_time.strftime('%I:%M %p') if meeting.start_time else 'TBD',
                    'Duration': f"{meeting.duration_minutes} min",
                    'Status': meeting.status.title(),
                    'Priority': meeting.priority.title()
                })
            
            df = pd.DataFrame(table_data)
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No meetings found. Use the Smart Chat to schedule your first meeting!")
    
    except Exception as e:
        st.error(f"Error loading dashboard: {e}")
        st.info("Please check your data source configuration.")


def show_calendar_view():
    """Show calendar view of meetings"""
    st.header("📅 Calendar View")
    
    try:
        # Date selector
        col1, col2 = st.columns([3, 1])
        with col1:
            view_date = st.date_input("Select Date", value=datetime.now().date())
        with col2:
            view_type = st.selectbox("View", ["Day", "Week", "Month"])
        
        meetings = get_meetings()
        
        if view_type == "Day":
            show_day_view(meetings, view_date)
        elif view_type == "Week":
            show_week_view(meetings, view_date)
        else:
            show_month_view(meetings, view_date)
    
    except Exception as e:
        st.error(f"Error loading calendar: {e}")


def show_day_view(meetings, selected_date):
    """Show day view of meetings"""
    day_meetings = [
        m for m in meetings 
        if m.start_time and m.start_time.date() == selected_date
    ]
    
    st.subheader(f"📅 {selected_date.strftime('%A, %B %d, %Y')}")
    
    if not day_meetings:
        st.info("No meetings scheduled for this day.")
        return
    
    # Sort by time
    day_meetings.sort(key=lambda m: m.start_time)
    
    for meeting in day_meetings:
        with st.expander(
            f"{meeting.start_time.strftime('%I:%M %p')} - {meeting.title} ({len(meeting.participants)} participants)"
        ):
            col1, col2 = st.columns([2, 1])
            with col1:
                if meeting.end_time:
                    st.write(f"**Time:** {meeting.start_time.strftime('%I:%M %p')} - {meeting.end_time.strftime('%I:%M %p')}")
                else:
                    st.write(f"**Time:** {meeting.start_time.strftime('%I:%M %p')}")
                st.write(f"**Duration:** {meeting.duration_minutes} minutes")
                if meeting.description:
                    st.write(f"**Description:** {meeting.description}")
                
                st.write("**Participants:**")
                for participant in meeting.participants:
                    st.write(f"  • {participant.name} ({participant.email})")
            
            with col2:
                st.write(f"**Status:** {meeting.status.title()}")
                st.write(f"**Priority:** {meeting.priority.title()}")
                
                # Status indicator
                if meeting.status == "scheduled":
                    st.success("✅ Confirmed")
                elif meeting.status == "draft":
                    st.warning("📝 Draft")
                else:
                    st.info("ℹ️ " + meeting.status.title())


def show_week_view(meetings, selected_date):
    """Show week view of meetings"""
    # Find start of week (Monday)
    week_start = selected_date - timedelta(days=selected_date.weekday())
    week_end = week_start + timedelta(days=6)
    
    st.subheader(f"📅 Week of {week_start.strftime('%B %d')} - {week_end.strftime('%B %d, %Y')}")
    
    # Filter meetings for the week
    week_meetings = [
        m for m in meetings 
        if m.start_time and week_start <= m.start_time.date() <= week_end
    ]
    
    if not week_meetings:
        st.info("No meetings scheduled for this week.")
        return
    
    # Group by day
    days_of_week = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    
    for i, day_name in enumerate(days_of_week):
        current_date = week_start + timedelta(days=i)
        day_meetings = [
            m for m in week_meetings 
            if m.start_time.date() == current_date
        ]
        
        st.write(f"**{day_name}, {current_date.strftime('%B %d')}**")
        
        if day_meetings:
            day_meetings.sort(key=lambda m: m.start_time)
            for meeting in day_meetings:
                st.write(f"  • {meeting.start_time.strftime('%I:%M %p')} - {meeting.title}")
        else:
            st.write("  *No meetings*")
        
        st.write("")


def show_month_view(meetings, selected_date):
    """Show month view of meetings"""
    st.subheader(f"📅 {selected_date.strftime('%B %Y')}")
    
    # Get first and last day of the month
    import calendar
    first_day = selected_date.replace(day=1)
    last_day = selected_date.replace(day=calendar.monthrange(selected_date.year, selected_date.month)[1])
    
    # Filter meetings for the month
    month_meetings = [
        m for m in meetings 
        if m.start_time and first_day <= m.start_time.date() <= last_day
    ]
    
    if not month_meetings:
        st.info("No meetings scheduled for this month.")
        return
    
    # Group by date
    meeting_counts = {}
    for meeting in month_meetings:
        dt = meeting.start_time.date()
        meeting_counts[dt] = meeting_counts.get(dt, 0) + 1
    
    # Create a simple calendar visualization
    st.write("**Meeting Distribution:**")
    for dt, count in sorted(meeting_counts.items()):
        st.write(f"  • {dt.strftime('%B %d')}: {count} meeting{'s' if count > 1 else ''}")


def show_participants_page():
    """Show participants management page"""
    st.header("👥 Participants")
    
    try:
        participants = get_participants()
        
        # Search functionality
        search_query = st.text_input("🔍 Search participants", placeholder="Type name or email...")
        
        if search_query:
            filtered_participants = [
                p for p in participants 
                if search_query.lower() in p.name.lower() or search_query.lower() in p.email.lower()
            ]
        else:
            filtered_participants = participants
        
        # Stats
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Participants", len(participants))
        with col2:
            departments = set(p.department for p in participants if p.department)
            st.metric("Departments", len(departments))
        with col3:
            available_count = len([p for p in participants if p.availability_status == "available"])
            st.metric("Available", available_count)
        
        # Participants table
        st.subheader(f"📋 All Participants ({len(filtered_participants)})")
        
        if filtered_participants:
            table_data = []
            for participant in filtered_participants:
                table_data.append({
                    'Name': participant.name,
                    'Email': participant.email,
                    'Department': participant.department or 'N/A',
                    'Title': participant.title or 'N/A',
                    'Status': participant.availability_status.title()
                })
            
            df = pd.DataFrame(table_data)
            st.dataframe(df, use_container_width=True)
            
            # Department breakdown
            if not search_query:
                st.subheader("📊 Department Breakdown")
                dept_counts = {}
                for p in participants:
                    dept = p.department or 'Unknown'
                    dept_counts[dept] = dept_counts.get(dept, 0) + 1
                
                if dept_counts:
                    fig = px.bar(
                        x=list(dept_counts.keys()), 
                        y=list(dept_counts.values()),
                        title="Participants by Department",
                        labels={'x': 'Department', 'y': 'Count'}
                    )
                    st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No participants found matching your search.")
    
    except Exception as e:
        st.error(f"Error loading participants: {e}")


def show_settings_page():
    """Show settings page"""
    st.header("⚙️ Settings")
    
    st.subheader("🔧 Application Settings")
    
    # System status
    with st.expander("📊 System Status", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            st.write("**Data Source:**", DATA_SOURCE.upper())
            st.write("**NLP Service:**", NLP_SERVICE_TYPE.upper())
        with col2:
            st.write("**Environment:** Development")
            st.write("**Python Version:** " + sys.version.split()[0])
            st.write("**Streamlit Version:** " + st.__version__)
    
    # Mock data management (if using mock data)
    if DATA_SOURCE == "mock":
        with st.expander("📊 Mock Data Management"):
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🔄 Reload Mock Data"):
                    data_service.load_from_file()
                    st.success("Mock data reloaded!")
                    safe_rerun()
            
            with col2:
                if st.button("💾 Save Mock Data"):
                    data_service.save_to_file()
                    st.success("Mock data saved!")
            
            st.write(f"**Current Data:**")
            st.write(f"  • {len(get_participants())} participants")
            st.write(f"  • {len(get_meetings())} meetings")
    
    # NLP Settings
    with st.expander("🧠 NLP Configuration"):
        if NLP_SERVICE_TYPE == "llm":
            st.success("✅ LLM NLP Active")
            st.write("Using advanced language model for parsing")
        elif NLP_SERVICE_TYPE == "simple":
            st.warning("⚠️ Simple NLP Active")
            st.write("Using regex-based parsing (no API key found)")
            st.info("Add an LLM API key to .env for better accuracy")
        else:
            st.error("❌ NLP Service Unavailable")
        
        st.write("**Supported Features:**")
        st.write("  • Name extraction")
        st.write("  • Date/time parsing")
        st.write("  • Duration recognition")
        st.write("  • Priority detection")
        st.write("  • Email extraction")
    
    # Integration Settings
    with st.expander("🔗 Integration Settings"):
        if DATA_SOURCE == "mock":
            st.warning("⚠️ Demo Mode - Using mock data")
            st.info("Configure Google Sheets in .env for production use")
        else:
            st.success("✅ Google Sheets Connected")
        
        st.write("**Phase 2 Features (Coming Soon):**")
        st.write("  • Microsoft 365 Calendar")
        st.write("  • Email notifications")
        st.write("  • Teams integration")
        st.write("  • Real-time availability")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        st.error(f"❌ Application error: {e}")
        st.info("The application encountered an error. Please check your configuration.")
        
        # Show error details in development
        if os.getenv('ENVIRONMENT') != 'production':
            with st.expander("🐛 Error Details"):
                import traceback
                st.code(traceback.format_exc())
