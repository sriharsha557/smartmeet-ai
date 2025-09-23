import streamlit as st
import os
import sys
from datetime import datetime, timedelta
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Add current directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

# Import our components
try:
    from components.chat_interface import chat_interface
    from utils.mock_data import mock_data
    from models import Meeting, Participant
    
    # Try to import full NLP service, fallback to simple version
    try:
        from services.nlp_service import nlp_service
        NLP_SERVICE_TYPE = "full"
    except ImportError:
        from services.nlp_service_simple import simple_nlp_service as nlp_service
        NLP_SERVICE_TYPE = "simple"
        
except ImportError as e:
    st.error(f"Error importing modules: {e}")
    st.info("Please ensure all files are in the correct directory structure.")
    st.stop()
# Compatibility fix for different Streamlit versions
def safe_rerun():
    """Safe rerun that works with different Streamlit versions"""
    try:
        st.rerun()  # New method in Streamlit >= 1.27
    except AttributeError:
        try:
            st.experimental_rerun()  # Older method
        except AttributeError:
            # Fallback - force refresh by setting a state variable
            if 'refresh_counter' not in st.session_state:
                st.session_state.refresh_counter = 0
            st.session_state.refresh_counter += 1

def fix_session_state_issues():
    """Fix common session state issues"""
    try:
        # Ensure required session state variables exist
        required_vars = [
            'app_initialized',
            'chat_history', 
            'current_meeting_draft',
            'participant_confirmations'
        ]
        
        for var in required_vars:
            if var not in st.session_state:
                if var == 'app_initialized':
                    st.session_state[var] = False
                elif var in ['chat_history', 'participant_confirmations']:
                    st.session_state[var] = {}
                else:
                    st.session_state[var] = None
                    
    except Exception as e:
        st.warning(f"Session state initialization warning: {e}")

def check_dependencies():
    """Check if all required dependencies are available"""
    missing_deps = []
    
    try:
        import pandas
    except ImportError:
        missing_deps.append("pandas")
    
    try:
        import plotly
    except ImportError:
        missing_deps.append("plotly")
    
    try:
        import nltk
    except ImportError:
        missing_deps.append("nltk")
    
    if missing_deps:
        st.error(f"Missing dependencies: {', '.join(missing_deps)}")
        st.info("Please install missing dependencies with: pip install " + " ".join(missing_deps))
        return False
    
    return True

def reset_application_state():
    """Reset application to clean state"""
    try:
        # Clear all session state
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        
        # Reinitialize essential state
        fix_session_state_issues()
        
        st.success("Application state reset successfully!")
        safe_rerun()
    except Exception as e:
        st.error(f"Error resetting application state: {e}")
# Page configuration
st.set_page_config(
    page_title="SmartMeet AI",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Replace the CSS section in your main.py with this:

st.markdown("""
<style>
.main-header {
    font-size: 3rem;
    font-weight: bold;
    text-align: center;
    margin-bottom: 2rem;
    color: #667eea;
    text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
}

/* Dark mode support */
.stApp[data-theme="dark"] .main-header {
    color: #a8b5ff;
}

.feature-card {
    padding: 1rem;
    border-radius: 10px;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    margin: 1rem 0;
}

.metric-card {
    background: var(--background-color);
    padding: 1rem;
    border-radius: 10px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    border-left: 4px solid #667eea;
    text-align: center;
    color: var(--text-color);
}

/* Dark mode support for metric cards */
.stApp[data-theme="dark"] .metric-card {
    background: #262730;
    box-shadow: 0 2px 4px rgba(255,255,255,0.1);
}

.chat-container {
    max-height: 600px;
    overflow-y: auto;
    padding: 1rem;
    background: var(--secondary-background-color);
    border-radius: 10px;
    margin-bottom: 1rem;
}

.stChatMessage {
    margin-bottom: 1rem;
}

/* Ensure text is visible in both themes */
.main-content {
    color: var(--text-color);
}

/* Fix for gradient text visibility */
@supports (-webkit-background-clip: text) {
    .main-header {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    
    /* Fallback for dark mode */
    .stApp[data-theme="dark"] .main-header {
        background: linear-gradient(90deg, #a8b5ff 0%, #c9a9ff 100%);
        -webkit-background-clip: text;
        background-clip: text;
        -webkit-text-fill-color: transparent;
    }
}

/* Fallback if gradient text isn't supported */
@supports not (-webkit-background-clip: text) {
    .main-header {
        color: #667eea !important;
        -webkit-text-fill-color: initial;
    }
    
    .stApp[data-theme="dark"] .main-header {
        color: #a8b5ff !important;
        -webkit-text-fill-color: initial;
    }
}
</style>
""", unsafe_allow_html=True)

def main():
    """Main application function"""
    
    # Initialize session state
    if 'app_initialized' not in st.session_state:
        st.session_state.app_initialized = True
        # Load mock data on first run
        mock_data.load_from_file()
    
    # Header
    st.markdown('<h1 class="main-header">🤖 SmartMeet AI</h1>', unsafe_allow_html=True)
    st.markdown('<p style="text-align: center; font-size: 1.2rem; color: #666;">Intelligent Meeting Scheduling Assistant</p>', unsafe_allow_html=True)

    # Sidebar
    with st.sidebar:
        st.title("🎯 Navigation")
        
        # Mock authentication status
        st.success("✅ Demo Mode Active")
        st.info("💡 Using mock data for testing")
        
        st.markdown("---")
        
        # Navigation menu
        page = st.selectbox(
            "Choose a page:",
            ["💬 Smart Chat", "🏠 Dashboard", "📅 Calendar View", "👥 Participants", "⚙️ Settings"]
        )
        
        st.markdown("---")
        
        # Quick stats
        st.markdown("### 📊 Quick Stats")
        meetings = mock_data.get_meetings()
        participants = mock_data.get_participants()
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Meetings", len(meetings))
        with col2:
            st.metric("People", len(participants))
        
        # Recent activity
        st.markdown("### 🕒 Recent")
        recent_meetings = sorted(meetings, key=lambda m: m.created_at, reverse=True)[:3]
        for meeting in recent_meetings:
            with st.expander(f"{meeting.title[:20]}...", expanded=False):
                st.write(f"**Participants:** {len(meeting.participants)}")
                st.write(f"**Status:** {meeting.status.title()}")
                if meeting.start_time:
                    st.write(f"**When:** {meeting.start_time.strftime('%m/%d %I:%M %p')}")

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
    chat_interface.render()

def show_dashboard():
    """Show dashboard with meeting overview"""
    st.header("🏠 Dashboard")
    
    # Get data
    meetings = mock_data.get_meetings()
    participants = mock_data.get_participants()
    
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
        st.markdown(f"""
        <div class="metric-card">
            <h3>📅 Today</h3>
            <h2>{len(today_meetings)}</h2>
            <p>meetings</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <h3>📊 This Week</h3>
            <h2>{len(this_week_meetings)}</h2>
            <p>meetings</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <h3>✅ Scheduled</h3>
            <h2>{len(scheduled_meetings)}</h2>
            <p>confirmed</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class="metric-card">
            <h3>📝 Drafts</h3>
            <h2>{len(draft_meetings)}</h2>
            <p>pending</p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")
    
    # Charts
    col1, col2 = st.columns(2)
    
    with col1:
        # Meeting frequency over time
        if meetings:
            meeting_dates = [m.start_time.date() for m in meetings if m.start_time]
            if meeting_dates:
                date_counts = {}
                for date in meeting_dates:
                    date_counts[date] = date_counts.get(date, 0) + 1
                
                df = pd.DataFrame(list(date_counts.items()), columns=['Date', 'Meetings'])
                df = df.sort_values('Date')
                
                fig = px.line(df, x='Date', y='Meetings', 
                             title='📈 Meeting Frequency Over Time',
                             markers=True)
                fig.update_layout(height=400)
                st.plotly_chart(fig, use_container_width=True)
    
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
    
    # Recent meetings table
    st.subheader("📋 Recent Meetings")
    
    if meetings:
        recent_meetings = sorted(meetings, key=lambda m: m.created_at, reverse=True)[:10]
        
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

def show_calendar_view():
    """Show calendar view of meetings"""
    st.header("📅 Calendar View")
    
    # Date selector
    col1, col2 = st.columns([3, 1])
    with col1:
        view_date = st.date_input("Select Date", value=datetime.now().date())
    with col2:
        view_type = st.selectbox("View", ["Day", "Week", "Month"])
    
    meetings = mock_data.get_meetings()
    
    if view_type == "Day":
        show_day_view(meetings, view_date)
    elif view_type == "Week":
        show_week_view(meetings, view_date)
    else:
        show_month_view(meetings, view_date)

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
                st.write(f"**Time:** {meeting.start_time.strftime('%I:%M %p')} - {meeting.end_time.strftime('%I:%M %p')}")
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
        date = meeting.start_time.date()
        meeting_counts[date] = meeting_counts.get(date, 0) + 1
    
    # Create a simple calendar visualization
    st.write("**Meeting Distribution:**")
    for date, count in sorted(meeting_counts.items()):
        st.write(f"  • {date.strftime('%B %d')}: {count} meeting{'s' if count > 1 else ''}")

def show_participants_page():
    """Show participants management page"""
    st.header("👥 Participants")
    
    participants = mock_data.get_participants()
    
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
        if not search_query:  # Only show for full list
            st.subheader("📊 Department Breakdown")
            dept_counts = {}
            for p in participants:
                dept = p.department or 'Unknown'
                dept_counts[dept] = dept_counts.get(dept, 0) + 1
            
            fig = px.bar(
                x=list(dept_counts.keys()), 
                y=list(dept_counts.values()),
                title="Participants by Department",
                labels={'x': 'Department', 'y': 'Count'}
            )
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No participants found matching your search.")

def show_settings_page():
    """Show settings page"""
    st.header("⚙️ Settings")
    
    st.subheader("🔧 Application Settings")
    
    # Mock data management
    with st.expander("📊 Mock Data Management"):
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 Reload Mock Data"):
                mock_data.load_from_file()
                st.success("Mock data reloaded!")
        
        with col2:
            if st.button("💾 Save Mock Data"):
                mock_data.save_to_file()
                st.success("Mock data saved!")
        
        st.write(f"**Current Data:**")
        st.write(f"  • {len(mock_data.get_participants())} participants")
        st.write(f"  • {len(mock_data.get_meetings())} meetings")
    
    # NLP Settings
    with st.expander("🧠 NLP Configuration"):
        st.info("Natural Language Processing is running with NLTK (basic mode)")
        st.write("**Supported Features:**")
        st.write("  • Name extraction")
        st.write("  • Date/time parsing")
        st.write("  • Duration recognition")
        st.write("  • Priority detection")
        st.write("  • Email extraction")
    
    # Integration Settings
    with st.expander("🔗 Integration Settings"):
        st.warning("⚠️ Demo Mode - All integrations are mocked")
        st.write("**Available when API access is enabled:**")
        st.write("  • Microsoft 365 Calendar")
        st.write("  • Email notifications")
        st.write("  • Teams integration")
        st.write("  • Real-time availability")
    
    # System Info
    with st.expander("ℹ️ System Information"):
        st.write("**Environment:** Demo/Development")
        st.write("**Python Version:** " + sys.version.split()[0])
        st.write("**Streamlit Version:** " + st.__version__)
        st.write("**Data Storage:** In-memory (session-based)")
        st.write("**NLP Engine:** NLTK + Custom Rules")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        st.error(f"Application error: {e}")
        st.info("The application is running in demo mode. Some features may be limited.")
        
        # Show error details in development
        if os.getenv('ENVIRONMENT') != 'production':
            st.code(f"Error details: {str(e)}")
            import traceback
            st.code(traceback.format_exc())
