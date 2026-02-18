import streamlit as st
import pandas as pd
import numpy as np
import time
from datetime import datetime

# --- CONFIGURATION ---
st.set_page_config(
    page_title="BioTwin: Growth Chamber Digital Twin",
    page_icon="🌱",
    layout="wide"
)

# --- STYLING ---
st.markdown("""
    <style>
    .metric-card {
        background-color: #f0f2f6;
        border-radius: 10px;
        padding: 20px;
        border: 1px solid #e6e9ef;
    }
    .status-good { color: #28a745; font-weight: bold; }
    .status-warn { color: #ffc107; font-weight: bold; }
    .status-danger { color: #dc3545; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- SESSION STATE INITIALIZATION ---
# We use session state to persist historical data across streamlit's experimental reruns
if 'history' not in st.session_state:
    st.session_state.history = pd.DataFrame(columns=[
        'Timestamp', 'Temperature', 'pH', 'Humidity', 'CO2', 'HealthScore'
    ])

# --- SIDEBAR CONTROLS ---
st.sidebar.header("🕹️ Chamber Controls")
st.sidebar.markdown("Adjust target parameters for the environment.")

target_temp = st.sidebar.slider("Target Temperature (°C)", 15.0, 45.0, 25.0, step=0.5)
mixer_speed = st.sidebar.slider("Mixer Speed (RPM)", 0, 1000, 300)

st.sidebar.divider()
st.sidebar.info("""
**Digital Twin Logic:**
The simulation uses a stochastic process (Gaussian noise) around your target values to simulate real sensor drift.
""")

# --- SIMULATION ENGINE ---
def generate_data(target_t):
    # Base values with realistic biological fluctuations using numpy
    temp = target_t + np.random.normal(0, 0.2)
    ph = 7.0 + np.random.normal(0, 0.05)
    humidity = 60.0 + np.random.normal(0, 1.5)
    co2 = 400.0 + np.random.normal(0, 10.0)
    
    # AI Predictive Analysis: Growth Health Score Calculation
    # Logic: Ideal temp is 22-28°C. Score drops as temp deviates.
    score = 100.0
    if temp > 32.0:
        score -= (temp - 32.0) * 15 # Heavy penalty for heat stress
    elif temp < 18.0:
        score -= (18.0 - temp) * 5
        
    score = max(0, min(100, score)) # Clip between 0-100
    
    return {
        'Timestamp': datetime.now().strftime("%H:%M:%S"),
        'Temperature': round(temp, 2),
        'pH': round(ph, 2),
        'Humidity': round(humidity, 1),
        'CO2': round(co2, 0),
        'HealthScore': round(score, 1)
    }

# --- MAIN DASHBOARD UI ---
st.title("🌱 BioTwin: Growth Chamber Digital Twin")
st.markdown(f"**Status:** Synchronized with virtual sensors | **Mixer:** {mixer_speed} RPM")

# Placeholders for real-time updates
metrics_placeholder = st.empty()
chart_placeholder = st.empty()
ai_analysis_placeholder = st.empty()

# --- REAL-TIME LOOP ---
# In a production app, we might use a fragment or a separate thread, 
# but for a Digital Twin sim, a simple loop with st.empty works best.
while True:
    # 1. Generate new data point
    new_data = generate_data(target_temp)
    
    # 2. Update History (keep last 50 data points for performance)
    new_row = pd.DataFrame([new_data])
    st.session_state.history = pd.concat([st.session_state.history, new_row], ignore_index=True).tail(50)
    
    # 3. Render Metrics
    with metrics_placeholder.container():
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Temperature", f"{new_data['Temperature']}°C", delta=f"{round(new_data['Temperature']-target_temp, 2)}°C")
        col2.metric("pH Level", f"{new_data['pH']}", delta="Optimal")
        col3.metric("Humidity", f"{new_data['Humidity']}%", delta="±1.2%")
        col4.metric("CO2 Concentration", f"{new_data['CO2']} ppm")

    # 4. Render AI Analysis & Warnings
    with ai_analysis_placeholder.container():
        st.subheader("🧠 AI Predictive Analysis")
        h_score = new_data['HealthScore']
        
        # UI Logic for Health Score
        if h_score > 80:
            st.success(f"**Growth Health Score: {h_score}/100** - Environment is Optimal.")
        elif 50 <= h_score <= 80:
            st.warning(f"**Growth Health Score: {h_score}/100** - Warning: Temperature variance detected.")
        else:
            st.error(f"**Growth Health Score: {h_score}/100** - CRITICAL: Heat stress detected in biological specimen!")
            st.toast("⚠️ Critical Alert: High Temperature Stress!", icon="🔥")

    # 5. Render Visuals
    with chart_placeholder.container():
        # Displaying two main charts
        c1, c2 = st.columns(2)
        with c1:
            st.write("Temperature History")
            st.line_chart(st.session_state.history.set_index('Timestamp')[['Temperature']])
        with c2:
            st.write("Health Score Trend")
            st.line_chart(st.session_state.history.set_index('Timestamp')[['HealthScore']])

    # 6. Frequency control
    time.sleep(1) 