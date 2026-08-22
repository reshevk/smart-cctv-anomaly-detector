import streamlit as st
import cv2
import numpy as np
from ultralytics import YOLO
import datetime
import tempfile
import time
import requests

# 1. Page Configuration
st.set_page_config(
    page_title="AEGIS | Smart CCTV Safety Monitor",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Telegram Bot Credentials
TELEGRAM_BOT_TOKEN = "8944820080:AAEunj6B_dpTfRZewxh7r-W95U4MhU_GO1A"
TELEGRAM_CHAT_ID = "8608774495"

# 2. Punchy Google Fonts & High-Contrast Visual Styling
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700;800&family=Space+Grotesk:wght@700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', sans-serif;
    }
    
    h1, h2, h3, .brand-title {
        font-family: 'Space Grotesk', sans-serif !important;
    }

    .stApp {
        background: radial-gradient(circle at 15% 15%, #121829 0%, #080b12 100%);
        color: #f8fafc;
    }

    .hero-box {
        background: linear-gradient(135deg, rgba(99, 102, 241, 0.2), rgba(236, 72, 153, 0.2));
        border: 1.5px solid rgba(255, 255, 255, 0.15);
        border-radius: 18px;
        padding: 20px 28px;
        margin-bottom: 20px;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.4);
    }
    
    .hero-title {
        font-size: 2.2rem;
        font-weight: 800;
        letter-spacing: -0.5px;
        background: linear-gradient(90deg, #38bdf8, #818cf8, #f472b6);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 0;
    }

    .hero-tagline {
        color: #cbd5e1;
        font-size: 1rem;
        font-weight: 500;
        margin-top: 4px;
    }

    .status-card {
        border-radius: 16px;
        padding: 24px;
        margin-bottom: 20px;
        display: flex;
        align-items: center;
        gap: 18px;
        box-shadow: 0 8px 24px rgba(0,0,0,0.35);
    }

    .status-normal {
        background: linear-gradient(135deg, rgba(16, 185, 129, 0.2), rgba(5, 150, 105, 0.08));
        border: 2px solid #10b981;
        color: #ecfdf5;
    }

    .status-fall {
        background: linear-gradient(135deg, rgba(239, 68, 68, 0.3), rgba(185, 28, 28, 0.15));
        border: 2px solid #ef4444;
        color: #fef2f2;
        animation: pulse-border 1.2s infinite;
    }

    .status-intrusion {
        background: linear-gradient(135deg, rgba(245, 158, 11, 0.3), rgba(217, 119, 6, 0.15));
        border: 2px solid #f59e0b;
        color: #fffbeb;
        animation: pulse-border 1.5s infinite;
    }

    @keyframes pulse-border {
        0% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.7); }
        70% { box-shadow: 0 0 0 16px rgba(239, 68, 68, 0); }
        100% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0); }
    }

    .metric-row {
        display: grid;
        grid-template-columns: repeat(2, 1fr);
        gap: 16px;
    }

    .metric-pill {
        background: rgba(30, 41, 59, 0.7);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 14px;
        padding: 18px;
        text-align: center;
    }

    .metric-label {
        font-size: 0.8rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.8px;
        color: #94a3b8;
    }

    .metric-num {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 2rem;
        font-weight: 700;
        margin-top: 6px;
    }
</style>
""", unsafe_allow_html=True)

# 3. Top Banner
st.markdown("""
<div class="hero-box">
    <div class="hero-title">AEGIS // SMART SAFETY MONITOR</div>
    <div class="hero-tagline">Real-time emergency fall detection & restricted perimeter security</div>
</div>
""", unsafe_allow_html=True)

# 4. Sidebar Controls
st.sidebar.markdown("### 🎛️ **Video Controls**")
input_source = st.sidebar.radio("Select Video Feed:", ("Live Webcam", "Upload Video File"))

if "last_alert_time" not in st.session_state:
    st.session_state.last_alert_time = 0

def send_telegram_alert(message):
    current_time = time.time()
    if current_time - st.session_state.last_alert_time > 10:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
        try:
            requests.post(url, json=payload, timeout=3)
            st.session_state.last_alert_time = current_time
        except Exception:
            pass

# 5. UI Layout
col_video, col_status = st.columns([1.7, 1.1])
video_placeholder = col_video.empty()
status_placeholder = col_status.empty()
metrics_placeholder = col_status.empty()

@st.cache_resource
def load_model():
    return YOLO("yolov8n-pose.pt")

model = load_model()

def process_stream(video_capture):
    fall_counter = 0
    intrusion_counter = 0

    while video_capture.isOpened():
        ret, frame = video_capture.read()
        if not ret:
            st.info("Video stream finished.")
            break

        h, w, _ = frame.shape
        zone_x1, zone_y1, zone_x2, zone_y2 = int(w * 0.6), int(h * 0.1), int(w * 0.95), int(h * 0.6)

        cv2.rectangle(frame, (zone_x1, zone_y1), (zone_x2, zone_y2), (245, 158, 11), 2)
        cv2.putText(frame, "RESTRICTED AREA", (zone_x1 + 10, zone_y1 + 25), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (245, 158, 11), 2)

        results = model(frame, conf=0.35, verbose=False)
        current_status = "NORMAL"
        badge_style = "status-normal"
        badge_icon = "🟢"
        badge_title = "AREA SECURE & SAFE"
        badge_desc = "Person is upright and active. No emergency detected."

        for result in results:
            boxes = result.boxes.xyxy.cpu().numpy() if result.boxes else []
            keypoints_all = result.keypoints.data.cpu().numpy() if result.keypoints is not None else []

            for idx, box in enumerate(boxes):
                bx1, by1, bx2, by2 = map(int, box[:4])
                box_w = bx2 - bx1
                box_h = by2 - by1
                cx, cy = (bx1 + bx2) // 2, (by1 + by2) // 2

                is_box_horizontal = box_w > (box_h * 0.95)
                is_skeleton_collapsed = False

                if len(keypoints_all) > idx:
                    kpts = keypoints_all[idx]
                    l_shoulder, r_shoulder = kpts[5], kpts[6]
                    l_hip, r_hip = kpts[11], kpts[12]

                    if (l_shoulder[2] > 0.3 or r_shoulder[2] > 0.3) and (l_hip[2] > 0.3 or r_hip[2] > 0.3):
                        shoulder_y = np.mean([pt[1] for pt in [l_shoulder, r_shoulder] if pt[2] > 0.3])
                        hip_y = np.mean([pt[1] for pt in [l_hip, r_hip] if pt[2] > 0.3])
                        if abs(shoulder_y - hip_y) < 55:
                            is_skeleton_collapsed = True

                if is_box_horizontal or is_skeleton_collapsed:
                    current_status = "FALL"
                    fall_counter += 1
                    badge_style = "status-fall"
                    badge_icon = "🚨"
                    badge_title = "EMERGENCY: FALL DETECTED"
                    badge_desc = "Person has fallen or collapsed on the floor. Sending help alert!"
                    
                    cv2.rectangle(frame, (bx1, by1), (bx2, by2), (239, 68, 68), 3)
                    cv2.putText(frame, "! FALL DETECTED !", (bx1, by1 - 10), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (239, 68, 68), 2)
                    
                    alert_msg = f"🚨 *AEGIS EMERGENCY ALERT*\n*Event:* Fall / Collapse Detected!\n*Time:* `{datetime.datetime.now().strftime('%H:%M:%S')}`\n*Location:* Camera 01"
                    send_telegram_alert(alert_msg)

                elif zone_x1 < cx < zone_x2 and zone_y1 < cy < zone_y2:
                    current_status = "INTRUSION"
                    intrusion_counter += 1
                    badge_style = "status-intrusion"
                    badge_icon = "⚠️"
                    badge_title = "WARNING: INTRUSION"
                    badge_desc = "Unauthorized movement inside restricted perimeter."
                    
                    cv2.rectangle(frame, (bx1, by1), (bx2, by2), (245, 158, 11), 3)
                    cv2.putText(frame, "! INTRUSION !", (bx1, by1 - 10), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (245, 158, 11), 2)
                    
                    alert_msg = f"⚠️ *AEGIS SECURITY ALERT*\n*Event:* Restricted Area Intrusion\n*Time:* `{datetime.datetime.now().strftime('%H:%M:%S')}`"
                    send_telegram_alert(alert_msg)

        annotated_frame = results[0].plot() if results else frame
        frame_rgb = cv2.cvtColor(annotated_frame, cv2.COLOR_BGR2RGB)
        video_placeholder.image(frame_rgb, channels="RGB", use_container_width=True)

        status_placeholder.markdown(f"""
        <div class="status-card {badge_style}">
            <div style="font-size: 2.5rem; line-height: 1;">{badge_icon}</div>
            <div>
                <div style="font-size: 1.25rem; font-weight: 800; letter-spacing: -0.3px;">{badge_title}</div>
                <div style="font-size: 0.95rem; opacity: 0.9; margin-top: 4px;">{badge_desc}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        metrics_placeholder.markdown(f"""
        <div class="metric-row">
            <div class="metric-pill">
                <div class="metric-label">Fall Alerts</div>
                <div class="metric-num" style="color: #f87171;">{fall_counter}</div>
            </div>
            <div class="metric-pill">
                <div class="metric-label">Intrusions</div>
                <div class="metric-num" style="color: #fbbf24;">{intrusion_counter}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        time.sleep(0.01)

    video_capture.release()

if input_source == "Live Webcam":
    start_cam = st.sidebar.checkbox("Start Webcam Feed", value=True)
    if start_cam:
        cap = cv2.VideoCapture(0)
        process_stream(cap)
    else:
        st.info("👈 Check 'Start Webcam Feed' in the sidebar to activate.")

elif input_source == "Upload Video File":
    uploaded_file = st.sidebar.file_uploader("Upload CCTV Clip (.mp4, .avi, .mov)", type=["mp4", "avi", "mov"])
    if uploaded_file is not None:
        tfile = tempfile.NamedTemporaryFile(delete=False)
        tfile.write(uploaded_file.read())
        cap = cv2.VideoCapture(tfile.name)
        process_stream(cap)
    else:
        st.info("👈 Upload a recorded CCTV video clip from the left sidebar.")
