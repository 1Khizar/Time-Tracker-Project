# streamlit_time_tracker.py
import streamlit as st
import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, date
import io
import matplotlib.pyplot as plt
import seaborn as sns

# ---------------------------
# Database helpers
# ---------------------------
DB_PATH = "time_tracker.db"

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    start_ts TEXT,
    end_ts TEXT,
    duration_minutes REAL,
    category TEXT,
    topic TEXT,
    notes TEXT,
    created_at TEXT
);
"""

CREATE_SETTINGS_SQL = """
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT
);
"""

def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    return conn

def init_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(CREATE_TABLE_SQL)
    cur.execute(CREATE_SETTINGS_SQL)
    conn.commit()
    conn.close()

init_db()

# ---------------------------
# Utility helpers
# ---------------------------
def now_ts():
    return datetime.now().isoformat()

def parse_ts(ts):
    if ts is None:
        return None
    return datetime.fromisoformat(ts)

def minutes_between(start_ts, end_ts):
    s = parse_ts(start_ts)
    e = parse_ts(end_ts)
    if s is None or e is None:
        return 0
    return (e - s).total_seconds() / 60.0

# ---------------------------
# DB operations
# ---------------------------
def insert_entry(start_ts, end_ts, duration_minutes, category, topic, notes):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO entries (start_ts, end_ts, duration_minutes, category, topic, notes, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (start_ts, end_ts, duration_minutes, category, topic, notes, now_ts()),
    )
    conn.commit()
    conn.close()

def fetch_entries():
    conn = get_conn()
    df = pd.read_sql_query(
        "SELECT * FROM entries ORDER BY start_ts DESC",
        conn,
        parse_dates=["start_ts", "end_ts", "created_at"]
    )
    conn.close()
    if df.empty:
        return df
    df['start_ts'] = pd.to_datetime(df['start_ts'], errors='coerce')
    df['end_ts'] = pd.to_datetime(df['end_ts'], errors='coerce')
    df['created_at'] = pd.to_datetime(df['created_at'], errors='coerce')
    return df

def update_entry(entry_id, **kwargs):
    conn = get_conn()
    cur = conn.cursor()
    fields = []
    values = []
    for k, v in kwargs.items():
        fields.append(f"{k} = ?")
        values.append(v)
    values.append(entry_id)
    sql = f"UPDATE entries SET {', '.join(fields)} WHERE id = ?"
    cur.execute(sql, values)
    conn.commit()
    conn.close()

def delete_entry(entry_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM entries WHERE id = ?", (entry_id,))
    conn.commit()
    conn.close()

def set_setting(key, value):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("REPLACE INTO settings (key, value) VALUES (?, ?)", (key, str(value)))
    conn.commit()
    conn.close()

def get_setting(key, default=None):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT value FROM settings WHERE key = ?", (key,))
    r = cur.fetchone()
    conn.close()
    if not r:
        return default
    return r[0]

# ---------------------------
# Helper functions for streaks and stats
# ---------------------------

def calculate_daily_streak(df):
    if df.empty:
        return 0
    valid_dates = df['start_ts'].dropna().dt.date
    if valid_dates.empty:
        return 0
    dates = sorted(set(valid_dates))
    streak = 0
    today = date.today()
    for i in range(len(dates)-1, -1, -1):
        expected_day = today - timedelta(days=streak)
        if dates[i] == expected_day:
            streak += 1
        elif dates[i] < expected_day:
            break
    return streak

def calculate_weekly_streak(df):
    if df.empty:
        return 0
    valid_weeks = df['start_ts'].dropna().dt.to_period('W').dt.start_time.dt.date
    if valid_weeks.empty:
        return 0
    weeks = sorted(set(valid_weeks))
    streak = 0
    this_week = (date.today() - timedelta(days=date.today().weekday()))  # Monday this week
    for i in range(len(weeks)-1, -1, -1):
        expected_week = this_week - timedelta(weeks=streak)
        if weeks[i] == expected_week:
            streak += 1
        elif weeks[i] < expected_week:
            break
    return streak

def calculate_monthly_streak(df):
    if df.empty:
        return 0
    valid_months = df['start_ts'].dropna().dt.to_period('M').dt.to_timestamp().dt.date
    if valid_months.empty:
        return 0
    months = sorted(set(valid_months))
    streak = 0
    today = date.today()
    current_month_start = today.replace(day=1)
    for i in range(len(months)-1, -1, -1):
        expected_month = (current_month_start - pd.DateOffset(months=streak)).date()
        if months[i] == expected_month:
            streak += 1
        elif months[i] < expected_month:
            break
    return streak

# ---------------------------
# Streamlit UI
# ---------------------------

st.set_page_config(page_title="Personal Time Tracker", layout="wide")
st.title("⏱ Personal Time Tracker")

# Sidebar controls
st.sidebar.header("Settings & Quick Controls")

default_cats = ["Study", "Project", "Work", "Entertainment", "Exercise", "Other"]
cats = st.sidebar.multiselect("Categories (choose or add)", options=default_cats, default=default_cats, key="sidebar_cats")
new_cat = st.sidebar.text_input("Add new category")
if new_cat:
    if new_cat not in cats:
        cats.append(new_cat)
    st.sidebar.success(f"Added category: {new_cat}")

daily_goal = st.sidebar.number_input("Daily goal (minutes)", min_value=0, value=int(get_setting('daily_goal') or 120))
set_setting('daily_goal', int(daily_goal))

st.sidebar.markdown("---")
if st.sidebar.button("Export all data to CSV"):
    df_all = fetch_entries()
    if df_all.empty:
        st.sidebar.warning("No data to export yet.")
    else:
        towrite = io.BytesIO()
        df_all.to_csv(towrite, index=False)
        towrite.seek(0)
        st.sidebar.download_button("Download CSV", towrite, file_name=f"time_tracker_{date.today().isoformat()}.csv")

st.sidebar.markdown("---")
st.sidebar.caption("Built with Streamlit • SQLite • pandas • matplotlib • seaborn")

# Fetch all entries
df_all = fetch_entries()

# Prepare date columns if not empty
if not df_all.empty:
    # Drop rows with missing start_ts to avoid NaT errors
    df_all = df_all.dropna(subset=['start_ts'])
    df_all['date'] = df_all['start_ts'].dt.date
    df_all['week'] = df_all['start_ts'].dt.to_period('W').dt.start_time.dt.date
    df_all['year_month'] = df_all['start_ts'].dt.to_period('M').dt.to_timestamp().dt.date

# --- Dashboard at top ---
st.subheader("📊 Dashboard & Reports")

if df_all.empty:
    st.info("No entries yet. Start the timer or add a manual entry to see reports.")
else:
    # Show Daily, Weekly, Monthly streaks
    daily_streak = calculate_daily_streak(df_all)
    weekly_streak = calculate_weekly_streak(df_all)
    monthly_streak = calculate_monthly_streak(df_all)

    # Today's total
    today = pd.Timestamp(date.today())
    df_today = df_all[df_all['start_ts'].dt.date == today.date()]
    total_today = df_today['duration_minutes'].sum()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Today's time", f"{int(total_today // 60)}h {int(total_today % 60)}m", delta=f"{int(total_today - daily_goal)//60}h {int((total_today - daily_goal)%60)}m")
    col2.metric("Daily Streak", f"{daily_streak} days")
    col3.metric("Weekly Streak", f"{weekly_streak} weeks")
    col4.metric("Monthly Streak", f"{monthly_streak} months")

    st.markdown("---")

    # Filters for reports
    st.markdown("*Filters*")
    cols = st.columns([1,1,1,1])
    with cols[0]:
        filter_cat = st.multiselect('Category', options=sorted(df_all['category'].dropna().unique()), default=sorted(df_all['category'].dropna().unique()), key='filter_cat')
    with cols[1]:
        min_date = st.date_input('From', value=df_all['date'].min(), key='min_date')
    with cols[2]:
        max_date = st.date_input('To', value=df_all['date'].max(), key='max_date')
    with cols[3]:
        group_by = st.selectbox('Group by', options=['date','week','year_month','category','topic'], index=0, key='group_by')

    mask = df_all['category'].isin(filter_cat) & (df_all['date'] >= min_date) & (df_all['date'] <= max_date)
    df_filtered = df_all[mask].copy()

    st.write('### Raw entries')
    st.dataframe(df_filtered[['id','start_ts','end_ts','duration_minutes','category','topic','notes']].sort_values('start_ts', ascending=False))

    # Edit / Delete entries
    st.markdown('---')
    st.subheader("✏️ Edit / Delete Entries")
    for idx, row in df_filtered.iterrows():
        with st.expander(f"Entry ID: {row['id']} - {row['category']} | {row['topic']}"):
            new_category = st.text_input(f"Category {row['id']}", value=row['category'], key=f"edit_cat_{row['id']}")
            new_topic = st.text_input(f"Topic {row['id']}", value=row['topic'], key=f"edit_topic_{row['id']}")

            # Separate date and time inputs
            new_start_date = st.date_input(f"Start Date {row['id']}", value=row['start_ts'].date(), key=f"start_date_{row['id']}")
            new_start_time = st.time_input(f"Start Time {row['id']}", value=row['start_ts'].time(), key=f"start_time_{row['id']}")
            new_end_date = st.date_input(f"End Date {row['id']}", value=row['end_ts'].date(), key=f"end_date_{row['id']}")
            new_end_time = st.time_input(f"End Time {row['id']}", value=row['end_ts'].time(), key=f"end_time_{row['id']}")

            new_notes = st.text_area(f"Notes {row['id']}", value=row['notes'], key=f"notes_{row['id']}")

            if st.button("Update", key=f"update_{row['id']}"):
                new_start = datetime.combine(new_start_date, new_start_time)
                new_end = datetime.combine(new_end_date, new_end_time)
                duration = (new_end - new_start).total_seconds() / 60.0
                if duration <= 0:
                    st.error("End time must be after start time!")
                else:
                    update_entry(row['id'], 
                        start_ts=new_start.isoformat(), 
                        end_ts=new_end.isoformat(), 
                        duration_minutes=duration, 
                        category=new_category, 
                        topic=new_topic,
                        notes=new_notes
                    )
                    st.success("Entry updated!")
                    st.experimental_rerun()

            if st.button("Delete", key=f"delete_{row['id']}"):
                delete_entry(row['id'])
                st.success("Entry deleted!")
                st.experimental_rerun()

    st.markdown('---')
    # Summary & charts
    st.write('### Summary')
    if group_by == 'date':
        summary = df_filtered.groupby('date')['duration_minutes'].sum().reset_index()
        summary = summary.sort_values('date')
        st.dataframe(summary)
        fig, ax = plt.subplots()
        sns.barplot(data=summary, x='date', y='duration_minutes', ax=ax)
        ax.set_ylabel('Minutes')
        plt.xticks(rotation=45)
        st.pyplot(fig)
    elif group_by == 'week':
        summary = df_filtered.groupby('week')['duration_minutes'].sum().reset_index()
        summary = summary.sort_values('week')
        st.dataframe(summary)
        fig, ax = plt.subplots()
        sns.barplot(data=summary, x='week', y='duration_minutes', ax=ax)
        ax.set_ylabel('Minutes')
        plt.xticks(rotation=45)
        st.pyplot(fig)
    elif group_by == 'year_month':
        summary = df_filtered.groupby('year_month')['duration_minutes'].sum().reset_index()
        summary['year_month'] = summary['year_month'].astype(str)
        st.dataframe(summary)
        fig, ax = plt.subplots()
        sns.barplot(data=summary, x='year_month', y='duration_minutes', ax=ax)
        ax.set_ylabel('Minutes')
        plt.xticks(rotation=45)
        st.pyplot(fig)
    elif group_by == 'category':
        summary = df_filtered.groupby('category')['duration_minutes'].sum().reset_index().sort_values('duration_minutes', ascending=False)
        st.dataframe(summary)
        fig, ax = plt.subplots()
        sns.barplot(data=summary, x='duration_minutes', y='category', orient='h', ax=ax)
        ax.set_xlabel('Minutes')
        st.pyplot(fig)
    elif group_by == 'topic':
        summary = df_filtered.groupby('topic')['duration_minutes'].sum().reset_index().sort_values('duration_minutes', ascending=False).head(30)
        st.dataframe(summary)
        fig, ax = plt.subplots()
        sns.barplot(data=summary, x='duration_minutes', y='topic', orient='h', ax=ax)
        ax.set_xlabel('Minutes')
        st.pyplot(fig)

    st.markdown('---')
    st.write('### Category distribution for selected range')
    dist = df_filtered.groupby('category')['duration_minutes'].sum().reset_index()
    if not dist.empty:
        fig2, ax2 = plt.subplots()
        ax2.pie(dist['duration_minutes'], labels=dist['category'], autopct='%1.1f%%', startangle=140)
        ax2.axis('equal')
        st.pyplot(fig2)

    st.markdown('---')
    st.write('### Download Filtered Data')
    buf = io.BytesIO()
    df_filtered.to_csv(buf, index=False)
    buf.seek(0)
    st.download_button('Download filtered CSV', buf, file_name='time_tracker_filtered.csv')

# --- Live Timer and Manual Entry below dashboard ---
st.markdown('---')
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("⏳ Live Timer")

    # Initialize session state for timer
    if 'running' not in st.session_state:
        st.session_state['running'] = False
    if 'paused' not in st.session_state:
        st.session_state['paused'] = False
    if 'start_time' not in st.session_state:
        st.session_state['start_time'] = None
    if 'elapsed_paused' not in st.session_state:
        st.session_state['elapsed_paused'] = timedelta(0)
    if 'pause_start' not in st.session_state:
        st.session_state['pause_start'] = None
    if 'start_category' not in st.session_state:
        st.session_state['start_category'] = None
    if 'start_topic' not in st.session_state:
        st.session_state['start_topic'] = None
    if 'start_notes' not in st.session_state:
        st.session_state['start_notes'] = None

    with st.form(key='timer_form'):
        category = st.selectbox("Category", options=cats, index=0)
        topic = st.text_input("Topic (optional)")
        notes = st.text_area("Notes (optional)")
        start_btn = st.form_submit_button("Start Timer")

    if start_btn and not st.session_state['running']:
        st.session_state['running'] = True
        st.session_state['paused'] = False
        st.session_state['start_time'] = datetime.now()
        st.session_state['elapsed_paused'] = timedelta(0)
        st.session_state['start_category'] = category
        st.session_state['start_topic'] = topic
        st.session_state['start_notes'] = notes
        st.success(f"Started: {category} - {topic} at {st.session_state['start_time'].strftime('%H:%M:%S')}")

    if st.session_state['running']:
        if st.session_state['paused']:
            st.markdown("*Timer is paused*")
            elapsed = st.session_state['pause_start'] - st.session_state['start_time'] - st.session_state['elapsed_paused']
        else:
            elapsed = datetime.now() - st.session_state['start_time'] - st.session_state['elapsed_paused']
            st.markdown("*Timer is running...*")
        st.markdown(f"*Started at:* {st.session_state['start_time'].strftime('%Y-%m-%d %H:%M:%S')}  ")
        # Show elapsed time in h m s format
        total_seconds = int(elapsed.total_seconds())
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        st.write(f"{hours}h {minutes}m {seconds}s")

        colp1, colp2, colp3 = st.columns([1,1,1])
        with colp1:
            if not st.session_state['paused']:
                if st.button("Pause"):
                    st.session_state['paused'] = True
                    st.session_state['pause_start'] = datetime.now()
            else:
                if st.button("Resume"):
                    # Update total paused duration
                    st.session_state['elapsed_paused'] += datetime.now() - st.session_state['pause_start']
                    st.session_state['paused'] = False
                    st.session_state['pause_start'] = None

        with colp2:
            if st.button("Stop & Save"):
                end_time = datetime.now()
                if st.session_state['paused']:
                    # Adjust end time if paused
                    end_time = st.session_state['pause_start']
                duration = (end_time - st.session_state['start_time'] - st.session_state['elapsed_paused']).total_seconds() / 60.0
                if duration > 0:
                    insert_entry(
                        st.session_state['start_time'].isoformat(),
                        end_time.isoformat(),
                        duration,
                        st.session_state['start_category'],
                        st.session_state['start_topic'],
                        st.session_state['start_notes']
                    )
                    st.success(f"Saved entry: {st.session_state['start_category']} for {int(duration)} minutes.")
                else:
                    st.warning("Duration is too short, not saved.")

                # Reset timer session state
                st.session_state['running'] = False
                st.session_state['paused'] = False
                st.session_state['start_time'] = None
                st.session_state['elapsed_paused'] = timedelta(0)
                st.session_state['pause_start'] = None
                st.session_state['start_category'] = None
                st.session_state['start_topic'] = None
                st.session_state['start_notes'] = None
                st.experimental_rerun()

        with colp3:
            if st.button("Cancel"):
                st.session_state['running'] = False
                st.session_state['paused'] = False
                st.session_state['start_time'] = None
                st.session_state['elapsed_paused'] = timedelta(0)
                st.session_state['pause_start'] = None
                st.session_state['start_category'] = None
                st.session_state['start_topic'] = None
                st.session_state['start_notes'] = None
                st.info("Timer cancelled.")
                st.experimental_rerun()

with col2:
    st.subheader("➕ Manual Entry")
    with st.form(key='manual_form'):
        m_start_date = st.date_input("Start Date", value=datetime.now())
        m_start_time = st.time_input("Start Time", value=datetime.now().time())
        m_end_date = st.date_input("End Date", value=datetime.now())
        m_end_time = st.time_input("End Time", value=datetime.now().time())
        m_category = st.selectbox("Category", options=cats, index=0)
        m_topic = st.text_input("Topic (optional)")
        m_notes = st.text_area("Notes (optional)")
        submit_manual = st.form_submit_button("Add Entry")

    if submit_manual:
        start_dt = datetime.combine(m_start_date, m_start_time)
        end_dt = datetime.combine(m_end_date, m_end_time)
        duration = (end_dt - start_dt).total_seconds() / 60.0
        if duration <= 0:
            st.error("End time must be after start time.")
        else:
            insert_entry(start_dt.isoformat(), end_dt.isoformat(), duration, m_category, m_topic, m_notes)
            st.success(f"Manual entry added: {m_category} for {int(duration)} minutes.")
            st.experimental_rerun()
