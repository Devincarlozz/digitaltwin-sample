import streamlit as st
import pandas as pd
import numpy as np
import time
from datetime import datetime

# --- CONFIGURATION ---
st.set_page_config(
    page_title="BioTwin: Growth Chamber Digital Twin",
    page_icon="🧬",
    layout="wide"
)

# --- SESSION STATE INITIALIZATION ---
if 'history' not in st.session_state:
    st.session_state.history = pd.DataFrame(columns=[
        'Timestamp', 'Temperature', 'pH', 'Humidity', 'CO2', 'HealthScore', 'Biomass'
    ])
if 'current_volume_ml' not in st.session_state:
    st.session_state.current_volume_ml = 100.0 # Starting at 100ml

# --- SIDEBAR CONTROLS ---
st.sidebar.header("🕹️ Chamber Controls")
target_temp = st.sidebar.slider("Target Temperature (°C)", 15.0, 45.0, 25.0, step=0.5)
mixer_speed = st.sidebar.slider("Mixer Speed (RPM)", 0, 1000, 300)

st.sidebar.divider()
st.sidebar.header("🧫 Cultivation Settings")
init_vol = st.sidebar.number_input("Initial Inoculum (ml)", value=100)
target_vol_l = st.sidebar.number_input("Target Harvest (Liters)", value=5.0)
growth_speed = st.sidebar.select_slider("Growth Multiplier", options=["Slow", "Standard", "Fast"], value="Standard")

# Reset Button
if st.sidebar.button("Reset Cultivation"):
    st.session_state.current_volume_ml = float(init_vol)
    st.session_state.history = pd.DataFrame(columns=['Timestamp', 'Temperature', 'pH', 'Humidity', 'CO2', 'HealthScore', 'Biomass'])
    st.rerun()

# --- BIOMASS LOGIC ---
def calculate_growth(current_ml, health_score, speed_setting):
    # Mapping growth speed to a base multiplier
    speed_map = {"Slow": 0.001, "Standard": 0.005, "Fast": 0.015}
    base_rate = speed_map[speed_setting]
    
    # Growth is dependent on health score (0.0 to 1.0 multiplier)
    # If health < 50, growth stalls or declines slightly
    health_factor = (health_score - 40) / 60 
    health_factor = max(-0.01, health_factor) # Can have slight decay if very unhealthy
    
    # Exponential growth formula: N(t) = N0 * e^(rt)
    # Simplified for 1-second ticks:
    new_volume = current_ml * (1 + (base_rate * health_factor))
    return max(0, new_volume)

# --- SIMULATION ENGINE ---
def generate_data(target_t, current_vol):
    temp = target_t + np.random.normal(0, 0.2)
    ph = 7.0 + np.random.normal(0, 0.05)
    humidity = 60.0 + np.random.normal(0, 1.5)
    co2 = 400.0 + np.random.normal(0, 10.0)
    
    # AI Predictive Health Score
    score = 100.0
    if temp > 32.0:
        score -= (temp - 32.0) * 15 
    elif temp < 18.0:
        score -= (18.0 - temp) * 5
    score = max(0, min(100, score))
    
    return {
        'Timestamp': datetime.now().strftime("%H:%M:%S"),
        'Temperature': round(temp, 2),
        'pH': round(ph, 2),
        'Humidity': round(humidity, 1),
        'CO2': round(co2, 0),
        'HealthScore': round(score, 1),
        'Biomass': round(current_vol / 1000, 3) # Convert to Liters for the chart
    }

# --- MAIN UI ---
st.title("🌱 BioTwin: Digital Twin & Cultivation Manager")

# Top Level Progress Bar
target_ml = target_vol_l * 1000
progress_pct = min(1.0, st.session_state.current_volume_ml / target_ml)

st.subheader(f"Total Progress: {round(progress_pct * 100, 1)}%")
st.progress(progress_pct)

# Metrics and UI segments
metrics_placeholder = st.empty()
ai_analysis_placeholder = st.empty()
chart_placeholder = st.empty()

# --- REAL-TIME LOOP ---
while True:
    # 1. Logic Update
    new_data = generate_data(target_temp, st.session_state.current_volume_ml)
    
    # Update biomass based on current health
    st.session_state.current_volume_ml = calculate_growth(
        st.session_state.current_volume_ml, 
        new_data['HealthScore'], 
        growth_speed
    )
    
    # 2. History Management
    new_row = pd.DataFrame([new_data])
    st.session_state.history = pd.concat([st.session_state.history, new_row], ignore_index=True).tail(50)
    
    # 3. Render Metrics
    with metrics_placeholder.container():
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Biomass (Liters)", f"{new_data['Biomass']} L", delta=f"{round(st.session_state.current_volume_ml - (new_data['Biomass']*1000), 2)} ml/s")
        m2.metric("Temp", f"{new_data['Temperature']}°C")
        m3.metric("pH", f"{new_data['pH']}")
        m4.metric("CO2", f"{new_data['CO2']} ppm")

    # 4. Render AI Status
    with ai_analysis_placeholder.container():
        h_score = new_data['HealthScore']
        col_a, col_b = st.columns([1, 3])
        
        with col_a:
            st.write("**Growth Status:**")
            if h_score > 80:
                st.success("OPTIMAL")
            elif h_score > 50:
                st.warning("STRESSED")
            else:
                st.error("STAGNANT")
        
        with col_b:
            if h_score < 50:
                st.error(f"Critical Heat Warning! Growth has halted. Current Score: {h_score}")
            else:
                st.info(f"Microbial doubling is active at {growth_speed} rate.")

    # 5. Render Charts
    with chart_placeholder.container():
        c1, c2 = st.columns(2)
        with c1:
            st.write("Biomass Accumulation (L)")
            st.line_chart(st.session_state.history.set_index('Timestamp')[['Biomass']])
        with c2:
            st.write("Environment Stability")
            st.line_chart(st.session_state.history.set_index('Timestamp')[['Temperature', 'HealthScore']])

    if progress_pct >= 1.0:
        st.balloons()
        st.success("Target Volume Achieved! Cultivation Ready for Harvest.")
        break

    time.sleep(1)
