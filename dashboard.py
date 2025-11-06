"""
dashboard.py

Streamlit dashboard page for SmartEval analytics and quick stats.

--- MODIFIED ---
- Added 'load_student_list' to read 'data/students.json'.
- 'load_all_evaluations' now loads from USN filenames.
- 'calculate_global_metrics' now calculates 'pending' and 'completion_pct'.
- 'display_dashboard' is updated with the new metric cards.
"""

import streamlit as st
import pandas as pd
import os
import json
from datetime import datetime
import plotly.graph_objects as go
from src.utils import save_json # Assuming utils.py has save_json

# --- Helper Functions ---

def load_student_list(student_file="data/students.json"):
    """Loads the master list of student USNs."""
    if not os.path.exists(student_file):
        st.error("CRITICAL: 'data/students.json' master list not found.")
        return []
    try:
        with open(student_file, "r") as f:
            return json.load(f)
    except Exception as e:
        st.error(f"Error loading student list: {e}")
        return []

def load_all_evaluations(scores_dir="outputs/scores"):
    """Loads all .json evaluation files from the scores directory."""
    if not os.path.exists(scores_dir):
        return []
        
    all_evals = []
    # Files are now named like '1AB19CS001.json'
    files = [f for f in os.listdir(scores_dir) if f.endswith(".json")]
    
    for fname in files:
        try:
            with open(os.path.join(scores_dir, fname), "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    all_evals.append(data)
        except Exception as e:
            print(f"Error reading {fname}: {e}")
            
    return all_evals

def calculate_global_metrics(all_evals: list, student_list: list) -> dict:
    """Calculates global metrics from all loaded evaluations."""
    
    total_papers = len(student_list)
    attempted_papers = len(all_evals)
    pending_papers = total_papers - attempted_papers
    completion_pct = (attempted_papers / total_papers * 100) if total_papers > 0 else 0
    
    total_score = 0
    total_max = 0
    
    for eval_data in all_evals:
        analytics = eval_data.get("analytics_data", {})
        total_data = analytics.get("total", {})
        
        # Use adjusted score if available, else original
        total_score += total_data.get("adjusted", total_data.get("original", 0))
        total_max += total_data.get("max", 0)
        
    average_score = (total_score / attempted_papers) if attempted_papers > 0 else 0
    average_score_max = (total_max / attempted_papers) if attempted_papers > 0 else 0
    avg_score_str = f"{average_score:.1f} / {average_score_max:.1f}" if attempted_papers > 0 else "N/A"

    return {
        "total_papers": total_papers,
        "attempted_papers": attempted_papers,
        "pending_papers": pending_papers,
        "completion_pct": f"{completion_pct:.1f}%",
        "average_score": avg_score_str
    }

# --- Main Display Function ---

def display_dashboard(subject_name):
    """Display the main dashboard with analytics and quick stats"""
    
    st.header(f"📈 Dashboard: {subject_name}")
    st.markdown("Here's a global overview of all evaluations processed by the system.")
    
    # Load data and calculate metrics
    student_list = load_student_list()
    all_evaluations = load_all_evaluations()
    metrics = calculate_global_metrics(all_evaluations, student_list)
    
    st.divider()

    # --- Top Metric Cards (as requested) ---
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
        st.metric(label="Total Papers", value=metrics["total_papers"])
        st.markdown('</div>', unsafe_allow_html=True)
    with col2:
        st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
        st.metric(label="Evaluated", value=metrics["attempted_papers"])
        st.markdown('</div>', unsafe_allow_html=True)
    with col3:
        st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
        st.metric(label="Pending", value=metrics["pending_papers"])
        st.markdown('</div>', unsafe_allow_html=True)
    with col4:
        st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
        st.metric(label="Completion %", value=metrics["completion_pct"])
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True) # Spacer

    # --- Main Dashboard Area (Charts and Recent Evals) ---
    col_main, col_side = st.columns([2, 1])

    with col_main:
        st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
        st.subheader("Performance Over Time")
        
        if all_evaluations:
            perf_data = []
            for eval_data in all_evaluations:
                analytics = eval_data.get("analytics_data", {})
                total_data = analytics.get("total", {})
                awarded = total_data.get("adjusted", total_data.get("original", 0))
                max_val = total_data.get("max", 100) 
                percentage = (awarded / max_val * 100) if max_val > 0 else 0
                
                perf_data.append({
                    "timestamp": pd.to_datetime(eval_data.get("timestamp", datetime.now())),
                    "score_percent": percentage
                })
            
            perf_df = pd.DataFrame(perf_data).sort_values(by="timestamp")
            
            fig = go.Figure(data=go.Scatter(
                x=perf_df["timestamp"],
                y=perf_df["score_percent"],
                mode='lines+markers',
                line=dict(color='#C48AF5', width=3), # Purple accent
                marker=dict(color='#FFFFFF', size=8)
            ))
            fig.update_layout(
                title_text='Average Score % (All Evals)',
                template="plotly_dark",
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                xaxis_title="Date",
                yaxis_title="Score (%)"
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No evaluation data yet. Run an evaluation to see performance charts.")
            
        st.markdown('</div>', unsafe_allow_html=True)

    with col_side:
        st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
        st.subheader("Recent Evaluations")
        
        if all_evaluations:
            # Sort by timestamp
            all_evaluations.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
            
            for eval_data in all_evaluations[:5]: # Show top 5 recent
                usn = eval_data.get("usn", "Unknown USN")
                timestamp_val = eval_data.get("timestamp")
                if timestamp_val:
                    ts = pd.to_datetime(timestamp_val).strftime("%Y-%m-%d %H:%M")
                else:
                    ts = "N/A"
                
                with st.container(border=True):
                    st.markdown(f"**🧑‍🎓 {usn}**")
                    st.caption(f"Evaluated: {ts}")
        else:
            st.info("No evaluations found.")
            
        st.markdown('</div>', unsafe_allow_html=True)

def save_evaluation_to_history(evaluation_data, history_path):
    """
    Saves the evaluation dictionary to a specific file path.
    The path is now the USN (e.g., 'outputs/scores/1AB19CS001.json').
    """
    try:
        # Assuming src.utils.save_json exists and works as expected
        from src.utils import save_json
        save_json(evaluation_data, history_path)
        return True
    except Exception as e:
        st.error(f"Error saving evaluation history: {e}")
        return False
