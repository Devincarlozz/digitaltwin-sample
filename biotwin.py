import streamlit as st
import pandas as pd
import numpy as np
import time
import google.generativeai as genai
from datetime import datetime
import json

# --- CONFIGURATION & API SETUP ---
st.set_page_config(page_title="BioTwin AI: Autonomous Chamber", page_icon="🤖", layout="wide")
GEMINI_API_KEY = st.secrets["AIzaSyDyPAHpqDJJVrfJi3llWWK644aQnP8ZqlM"]
# Securely setting the API Key
GEMINI_API_KEY = "AIzaSyDyPAHpqDJJVrfJi3llWWK644aQnP8ZqlM"
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# --- SESSION STATE INITIALIZATION ---
if 'history' not in st.session_state:
    st.session_state.history = pd.DataFrame(columns=[
        'Timestamp', 'Temperature', 'pH', 'Humidity', 'CO2', 'HealthScore', 'Biomass'
    ])
if 'current_volume_ml' not in st.session_state:
    st.session_state.current_volume_ml = 100.0
if 'ai_setpoints' not in st.session_state:
    # Initial safe defaults
    st.session_state.ai_setpoints = {"target_temp": 25.0, "mixer_speed": 300}
if 'ai_reasoning' not in st.session_state:
    st.session_state.ai_reasoning = "System initializing..."

# --- AI AUTONOMOUS CONTROLLER ---
def ask_gemini_to_control(current_data):
    """Sends sensor data to Gemini and receives control instructions."""
    prompt = f"""
    You are an AI Bio-Chamber Controller. Your goal is to keep microbial growth at 100% health.
    Current Sensor Data:
    - Temperature: {current_data['Temperature']}°C
    - pH: {current_data['pH']}
    - Humidity: {current_data['Humidity']}%
    - CO2: {current_data['CO2']} ppm
    - Current Biomass: {current_data['Biomass']} L

    Optimal Conditions: Temp 28°C, pH 7.0, Mixer 400RPM.
    If Temp > 30°C, microbes start dying. 
    
    Respond ONLY in a valid JSON format like this:
    {{"target_temp": 28.0, "mixer_speed": 400, "reasoning": "Brief explanation of change"}}
    """
    try:
        response = model.generate_content(prompt)
        # Clean the response to ensure valid JSON
        clean_json = response.text.replace('```json', '').replace('```', '').strip()
        return json.loads(clean_json)
    except Exception as e:
        return None

# --- GROWTH SIMULATION ENGINE ---
def generate_environment(target_temp, current_vol):
    # Simulate environmental noise/drift
    drift = np.random.normal(0, 0.5) 
    temp = target_temp + drift
    ph = 7.0 + np.random.normal(0, 0.1)
    hum = 65.0 + np.random.normal(0, 2)
    co2 = 450.0 + np.random.normal(0, 20)
    
    # Calculate Health Score based on deviation from optimal (28°C)
    score = 100 - (abs(temp - 28.0) * 12)
    score = max(0, min(100, score))
    
    # Growth Calculation (Exponential)
    growth_rate = 0.008 * (score / 100)
    new_vol = current_vol * (1 + growth_rate)
    
    return {
        'Timestamp': datetime.now().strftime("%H:%M:%S"),
        'Temperature': round(temp, 2),
        'pH': round(ph, 2),
        'Humidity': round(hum, 1),
        'CO2': round(co2, 0),
        'HealthScore': round(score, 1),
        'Biomass': round(new_vol / 1000, 3)
    }, new_vol

# --- UI LAYOUT ---
st.title("🧪 BioTwin: Gemini-Powered Autonomous Digital Twin")
st.markdown("This chamber is currently under **Full AI Control**. Manual sliders have been disabled.")

# Top Progress Section
target_l = 5.0
progress_pct = min(1.0, (st.session_state.current_volume_ml / 1000) / target_l)
st.metric("Total Cultivation Progress", f"{round(progress_pct*100, 2)}%")
st.progress(progress_pct)

# Sidebar: AI Monitor
st.sidebar.header("🤖 AI Controller Status")
st.sidebar.write(f"**Target Temp:** {st.session_state.ai_setpoints['target_temp']}°C")
st.sidebar.write(f"**Mixer Speed:** {st.session_state.ai_setpoints['mixer_speed']} RPM")
st.sidebar.divider()
st.sidebar.subheader("AI Reasoning:")
st.sidebar.info(st.session_state.ai_reasoning)

# Placeholders
metrics_row = st.empty()
charts_row = st.empty()

# --- MAIN LOOP ---
count = 0
while progress_pct < 1.0:
    # 1. Generate current state based on AI's last setpoints
    data_point, st.session_state.current_volume_ml = generate_environment(
        st.session_state.ai_setpoints['target_temp'], 
        st.session_state.current_volume_ml
    )
    
    # 2. Update History
    new_row = pd.DataFrame([data_point])
    st.session_state.history = pd.concat([st.session_state.history, new_row], ignore_index=True).tail(30)
    
    # 3. AI CONTROL STEP (Every 5 seconds to avoid API spam)
    if count % 5 == 0:
        with st.spinner("Gemini analyzing sensor drift..."):
            ai_command = ask_gemini_to_control(data_point)
            if ai_command:
                st.session_state.ai_setpoints['target_temp'] = ai_command.get('target_temp', 28.0)
                st.session_state.ai_setpoints['mixer_speed'] = ai_command.get('mixer_speed', 400)
                st.session_state.ai_reasoning = ai_command.get('reasoning', "Maintaining stability.")

    # 4. Update Metrics Display
    with metrics_row.container():
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Live Temp", f"{data_point['Temperature']}°C", 
                  delta=f"{round(data_point['Temperature'] - 28.0, 2)} from Optimal")
        c2.metric("Health Score", f"{data_point['HealthScore']}%")
        c3.metric("Biomass", f"{data_point['Biomass']} L")
        c4.metric("AI Stability", "ACTIVE", delta_color="normal")

    # 5. Update Charts
    with charts_row.container():
        col_left, col_right = st.columns(2)
        with col_left:
            st.write("### Real-time Growth (L)")
            st.line_chart(st.session_state.history.set_index('Timestamp')[['Biomass']])
        with col_right:
            st.write("### AI Corrective Action (Temp vs Health)")
            st.line_chart(st.session_state.history.set_index('Timestamp')[['Temperature', 'HealthScore']])

    count += 1
    time.sleep(1)

if progress_pct >= 1.0:
    st.balloons()
    st.success("Target achieved! Gemini successfully managed the cultivation process.")
