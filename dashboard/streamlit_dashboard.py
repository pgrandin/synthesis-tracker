#!/usr/bin/env python3
"""
Synthesis Activity Dashboard
Run with: streamlit run streamlit_dashboard.py
"""

import streamlit as st
import pandas as pd
import json
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path

# Page config
st.set_page_config(
    page_title="Synthesis Tracker Dashboard",
    page_icon="🧠",
    layout="wide"
)

@st.cache_data
def load_data():
    """Load data from JSON file"""
    data_file = Path(__file__).parent.parent / "email_parser" / "synthesis_data.json"

    with open(data_file, 'r') as f:
        data = json.load(f)

    return data

def parse_date(date_str):
    """Parse email date string to datetime"""
    try:
        # Parse RFC 2822 format - handle both single and double digit days
        from email.utils import parsedate_to_datetime
        return parsedate_to_datetime(date_str)
    except:
        try:
            # Fallback to manual parsing
            return datetime.strptime(date_str[:25], '%a, %d %b %Y %H:%M:%S')
        except:
            return None

def create_weekly_chart(progress_data):
    """Create weekly activity chart"""
    # Prepare data
    weeks = []
    for p in progress_data:
        date = parse_date(p.get('date', ''))
        if date and 'total_weekly_minutes' in p:
            weeks.append({
                'Week': date.strftime('%Y-%m-%d'),
                'Minutes': p['total_weekly_minutes'],
                'Active Days': sum(1 for v in p.get('daily_minutes', {}).values() if v > 0)
            })

    if not weeks:
        return None

    df = pd.DataFrame(weeks).sort_values('Week')

    # Create bar chart
    fig = px.bar(
        df,
        x='Week',
        y='Minutes',
        hover_data=['Active Days'],
        title='Weekly Activity (Minutes)',
        labels={'Minutes': 'Total Minutes', 'Week': 'Week Starting'},
        color='Minutes',
        color_continuous_scale='Blues'
    )

    fig.update_layout(height=400)
    return fig

def create_daily_breakdown(progress_data):
    """Create daily activity heatmap"""
    # Get most recent week with daily data
    recent = None
    for p in sorted(progress_data, key=lambda x: x.get('email_id', 0), reverse=True):
        if 'daily_minutes' in p:
            recent = p
            break

    if not recent or not recent.get('daily_minutes'):
        return None

    days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
    values = [recent['daily_minutes'].get(d, 0) for d in days]

    fig = go.Figure(data=[
        go.Bar(
            x=days,
            y=values,
            marker_color=['green' if v > 0 else 'lightgray' for v in values],
            text=values,
            textposition='auto'
        )
    ])

    date = parse_date(recent.get('date', ''))
    title_date = date.strftime('%B %d, %Y') if date else 'Most Recent Week'

    fig.update_layout(
        title=f'Daily Activity - Week of {title_date}',
        yaxis_title='Minutes',
        height=300
    )

    return fig

def create_session_timeline(session_data):
    """Create session timeline"""
    sessions = []
    for s in session_data:
        date = parse_date(s.get('date', ''))
        if date and 'duration_minutes' in s:
            sessions.append({
                'Date': date,
                'Duration': s['duration_minutes'],
                'Day': s.get('day', 'Unknown'),
                'Time': s.get('time', 'Unknown'),
                'Topic': s.get('topic', 'No topic')[:30]
            })

    if not sessions:
        return None

    df = pd.DataFrame(sessions).sort_values('Date')

    fig = px.scatter(
        df,
        x='Date',
        y='Duration',
        size='Duration',
        hover_data=['Day', 'Time', 'Topic'],
        title='Individual Sessions',
        labels={'Duration': 'Duration (minutes)'},
        color='Duration',
        color_continuous_scale='Viridis'
    )

    fig.update_layout(height=400)
    return fig

def main():
    st.title("🧠 Synthesis Tutor Activity Dashboard")

    # Load data
    try:
        data = load_data()
    except FileNotFoundError:
        st.error("No data found. Run `python3 synthesis_tracker.py` first to generate data.")
        return

    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)

    summary = data.get('summary', {})

    with col1:
        st.metric(
            "Total Weeks Tracked",
            summary.get('week_count', 0)
        )

    with col2:
        st.metric(
            "Avg Weekly Minutes",
            f"{summary.get('avg_weekly_minutes', 0):.0f}"
        )

    with col3:
        st.metric(
            "Total Sessions",
            summary.get('session_count', 0)
        )

    with col4:
        st.metric(
            "Avg Session Minutes",
            f"{summary.get('avg_session_minutes', 0):.0f}"
        )

    # Show last activity info
    progress = sorted(data.get('progress', []), key=lambda x: x.get('email_id', 0), reverse=True)
    if progress and progress[0].get('total_weekly_minutes') > 0:
        last_week = progress[0]
        last_date = parse_date(last_week.get('date', ''))
        if last_date:
            st.info(f"📅 Last activity: Week of {last_date.strftime('%B %d, %Y')} - {last_week.get('total_weekly_minutes', 0)} minutes")

    # Charts
    st.header("📊 Activity Trends")

    # Weekly activity chart
    weekly_chart = create_weekly_chart(data.get('progress', []))
    if weekly_chart:
        st.plotly_chart(weekly_chart, use_container_width=True)

    # Two column layout for other charts
    col1, col2 = st.columns(2)

    with col1:
        # Daily breakdown
        daily_chart = create_daily_breakdown(data.get('progress', []))
        if daily_chart:
            st.plotly_chart(daily_chart, use_container_width=True)

    with col2:
        # Session timeline
        session_chart = create_session_timeline(data.get('sessions', []))
        if session_chart:
            st.plotly_chart(session_chart, use_container_width=True)

    # Recent activity details
    st.header("📝 Activity Details")

    tab1, tab2 = st.tabs(["Session History (Jul-Aug)", "Weekly Reports (Jun-Sep)"])

    with tab1:
        sessions = sorted(
            data.get('sessions', []),
            key=lambda x: x.get('email_id', 0),
            reverse=True
        )[:10]

        if sessions:
            session_df = pd.DataFrame([
                {
                    'Date': parse_date(s.get('date', '')).strftime('%Y-%m-%d') if parse_date(s.get('date', '')) else 'Unknown',
                    'Day': s.get('day', ''),
                    'Time': s.get('time', ''),
                    'Duration (min)': s.get('duration_minutes', 0),
                    'Topic': s.get('topic', '')[:40]
                }
                for s in sessions
            ])
            st.dataframe(session_df, use_container_width=True)

    with tab2:
        progress = sorted(
            data.get('progress', []),
            key=lambda x: x.get('email_id', 0),
            reverse=True
        )[:10]

        if progress:
            progress_df = pd.DataFrame([
                {
                    'Week': parse_date(p.get('date', '')).strftime('%Y-%m-%d') if parse_date(p.get('date', '')) else 'Unknown',
                    'Total Minutes': p.get('total_weekly_minutes', 0),
                    'Active Days': sum(1 for v in p.get('daily_minutes', {}).values() if v > 0),
                    'Daily Breakdown': ', '.join([f"{d[:3]}:{m}" for d, m in p.get('daily_minutes', {}).items() if m > 0])
                }
                for p in progress
            ])
            st.dataframe(progress_df, use_container_width=True)

    # Refresh button
    st.sidebar.header("⚙️ Controls")
    if st.sidebar.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()

    st.sidebar.info(
        "Data is loaded from `synthesis_data.json`. "
        "Run `python3 synthesis_tracker.py` to update."
    )

if __name__ == "__main__":
    main()