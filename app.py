import streamlit as st
import time
from datetime import datetime, timedelta
import pandas as pd

# Page configuration
st.set_page_config(
    page_title="Study Time Tracker",
    page_icon="📚",
    layout="centered"
)

# Initialize session state
if 'total_study_time' not in st.session_state:
    st.session_state.total_study_time = 0

if 'sessions' not in st.session_state:
    st.session_state.sessions = []

if 'timer_running' not in st.session_state:
    st.session_state.timer_running = False

if 'session_start_time' not in st.session_state:
    st.session_state.session_start_time = None

if 'current_session_time' not in st.session_state:
    st.session_state.current_session_time = 0

if 'current_category' not in st.session_state:
    st.session_state.current_category = "General"

if 'current_project' not in st.session_state:
    st.session_state.current_project = ""

# Default categories
DEFAULT_CATEGORIES = ["General", "Math", "Science", "Programming", "Languages", "Reading", "Research"]

# Helper functions
def format_time_seconds(seconds):
    """Format seconds to HH:MM:SS"""
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"

def format_total_time(seconds):
    """Format total time to hours and minutes"""
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    if hours > 0:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"

def start_timer():
    """Start the timer"""
    st.session_state.timer_running = True
    st.session_state.session_start_time = time.time()

def stop_timer():
    """Stop the timer and save session"""
    if st.session_state.timer_running and st.session_state.session_start_time:
        session_duration = int(time.time() - st.session_state.session_start_time)
        if session_duration > 0:
            new_session = {
                'duration': session_duration,
                'type': 'Timer',
                'time': datetime.now().strftime('%H:%M:%S'),
                'id': len(st.session_state.sessions) + 1,
                'category': st.session_state.current_category,
                'project': st.session_state.current_project,
                'notes': ""
            }
            st.session_state.sessions.append(new_session)
            st.session_state.total_study_time += session_duration
    
    st.session_state.timer_running = False
    st.session_state.session_start_time = None
    st.session_state.current_session_time = 0

def add_manual_time(hours, minutes, category, project, notes):
    """Add manual study time"""
    total_seconds = (hours * 3600) + (minutes * 60)
    if total_seconds > 0:
        new_session = {
            'duration': total_seconds,
            'type': 'Manual',
            'time': datetime.now().strftime('%H:%M:%S'),
            'id': len(st.session_state.sessions) + 1,
            'category': category,
            'project': project,
            'notes': notes
        }
        st.session_state.sessions.append(new_session)
        st.session_state.total_study_time += total_seconds

def remove_session(session_id):
    """Remove a session"""
    for i, session in enumerate(st.session_state.sessions):
        if session['id'] == session_id:
            st.session_state.total_study_time -= session['duration']
            st.session_state.sessions.pop(i)
            break

# Calculate current session time
if st.session_state.timer_running and st.session_state.session_start_time:
    st.session_state.current_session_time = int(time.time() - st.session_state.session_start_time)

# Main UI
st.title("📚 Study Time Tracker")

# Display current date
today = datetime.now().strftime('%A, %B %d, %Y')
st.markdown(f"<p style='text-align: center; color: #666;'>{today}</p>", unsafe_allow_html=True)

# Total study time display
st.markdown("---")
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    st.markdown(f"""
    <div style='
        background: linear-gradient(90deg, #3b82f6, #6366f1);
        color: white;
        padding: 20px;
        border-radius: 15px;
        text-align: center;
        margin: 20px 0;
    '>
        <h3 style='margin: 0; color: white;'>🕒 Total Study Time</h3>
        <h1 style='margin: 10px 0; color: white; font-size: 2.5em;'>{format_total_time(st.session_state.total_study_time)}</h1>
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")

# Current Session Timer
st.subheader("⏱ Current Session")

# Category and Project for timer
col1, col2 = st.columns(2)
with col1:
    st.session_state.current_category = st.selectbox("Category", DEFAULT_CATEGORIES, key="timer_category")
with col2:
    st.session_state.current_project = st.text_input("Project (optional)", key="timer_project")

# Timer display
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    timer_placeholder = st.empty()
    timer_placeholder.markdown(f"""
    <div style='
        font-size: 3em;
        font-family: monospace;
        text-align: center;
        background-color: #f8f9fa;
        padding: 20px;
        border-radius: 10px;
        margin: 10px 0;
    '>
        {format_time_seconds(st.session_state.current_session_time)}
    </div>
    """, unsafe_allow_html=True)

# Timer controls
col1, col2, col3, col4, col5 = st.columns([1, 1, 1, 1, 1])

with col2:
    if not st.session_state.timer_running:
        if st.button("▶ Start", use_container_width=True, type="primary"):
            start_timer()
            st.rerun()

with col3:
    if st.session_state.timer_running:
        if st.button("⏸ Pause", use_container_width=True, type="secondary"):
            st.session_state.timer_running = False
            st.rerun()

with col4:
    if st.button("⏹ Stop", use_container_width=True, type="secondary"):
        stop_timer()
        st.rerun()

# Auto-refresh when timer is running
if st.session_state.timer_running:
    time.sleep(1)
    st.rerun()

st.markdown("---")

# Manual time entry
st.subheader("➕ Add Manual Time")

col1, col2 = st.columns(2)

with col1:
    manual_hours = st.number_input("Hours", min_value=0, max_value=23, value=0, key="manual_hours")
    manual_category = st.selectbox("Category", DEFAULT_CATEGORIES, key="manual_category")

with col2:
    manual_minutes = st.number_input("Minutes", min_value=0, max_value=59, value=0, key="manual_minutes")
    manual_project = st.text_input("Project (optional)", key="manual_project")

manual_notes = st.text_area("Notes (optional)", height=80, key="manual_notes")

if st.button("➕ Add Time", use_container_width=True, type="primary"):
    if manual_hours > 0 or manual_minutes > 0:
        add_manual_time(manual_hours, manual_minutes, manual_category, manual_project, manual_notes)
        st.success(f"Added {manual_hours}h {manual_minutes}m to your study time!")
        st.rerun()
    else:
        st.warning("Please enter hours or minutes to add.")

st.markdown("---")

# Session History
if st.session_state.sessions:
    st.subheader("📋 Today's Sessions")
    
    for i, session in enumerate(reversed(st.session_state.sessions)):
        with st.container():
            col1, col2 = st.columns([4, 1])
            
            with col1:
                # Main session info
                st.write(f"{format_total_time(session['duration'])}** - {session['type']} ({session['time']})")
                
                # Category and project
                info_parts = []
                if session.get('category'):
                    info_parts.append(f"📂 {session['category']}")
                if session.get('project'):
                    info_parts.append(f"🎯 {session['project']}")
                
                if info_parts:
                    st.write(" | ".join(info_parts))
                
                # Notes
                if session.get('notes'):
                    st.write(f"📝 {session['notes']}")
            
            with col2:
                if st.button("🗑 Remove", key=f"remove_{session['id']}", type="secondary"):
                    remove_session(session['id'])
                    st.rerun()
            
            st.markdown("<hr style='margin: 10px 0;'>", unsafe_allow_html=True)

# Statistics
if st.session_state.sessions:
    st.markdown("---")
    st.subheader("📊 Statistics")
    
    total_sessions = len(st.session_state.sessions)
    timer_sessions = len([s for s in st.session_state.sessions if s['type'] == 'Timer'])
    manual_sessions = len([s for s in st.session_state.sessions if s['type'] == 'Manual'])
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total Sessions", total_sessions)
    
    with col2:
        st.metric("Timer Sessions", timer_sessions)
    
    with col3:
        st.metric("Manual Sessions", manual_sessions)
    
    # Category breakdown
    if st.session_state.sessions:
        st.markdown("### 📂 Time by Category")
        category_time = {}
        for session in st.session_state.sessions:
            category = session.get('category', 'General')
            if category in category_time:
                category_time[category] += session['duration']
            else:
                category_time[category] = session['duration']
        
        for category, total_time in category_time.items():
            st.write(f"{category}:** {format_total_time(total_time)}")

# Instructions
with st.expander("📖 How to Use"):
    st.markdown("""
    *Timer Mode:*
    - Select category and project before starting
    - Click "▶ Start" to begin timing your study session
    - Click "⏸ Pause" to pause the timer (you can resume by clicking Start again)
    - Click "⏹ Stop" to end the session and add it to your total time
    
    *Manual Mode:*
    - Enter the number of hours and minutes you studied
    - Choose category and project (optional)
    - Add notes about what you studied (optional)
    - Click "➕ Add Time" to add it to your total
    - Perfect for offline study time or when you forgot to start the timer
    
    *Categories & Organization:*
    - Use categories to organize your study subjects (Math, Science, etc.)
    - Add project names for specific assignments or topics
    - Notes help you remember what you studied
    
    *Session Management:*
    - View all your study sessions with categories and notes
    - See time breakdown by category in statistics
    - Remove any incorrect entries by clicking the "🗑 Remove" button
    
    *Note:* This tracker resets when you refresh the page or restart the Streamlit app.
    """)

# Footer
st.markdown("---")
st.markdown("<p style='text-align: center; color: #666;'>Keep studying! 💪📚</p>", unsafe_allow_html=True)