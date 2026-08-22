import streamlit as st
import cv2
import numpy as np
from ultralytics import YOLO
import datetime
import tempfile
import time
import requests
import av
from streamlit_webrtc import webrtc_streamer, WebRtcMode, RTCConfiguration

# 1. Page Configuration
st.set_page_config(
    page_title="AEGIS | Smart CCTV Safety Monitor",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Telegram Credentials
TELEGRAM_BOT_TOKEN = "8944820080:AAEunj6B_dpTfRZewxh7r-W95U4MhU_GO1A"
TELEGRAM_CHAT_ID = "8608774495"

# STUN server for WebRTC cloud connectivity
RTC_CONFIG = RTCConfiguration(
    {"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]}
)

# 2. Styling
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700;800&family=Space+Grotesk:wght@700&display=swap');
    html, body, [class*="css"] { font-family: 'Plus Jakarta Sans', sans-serif; }
    h1, h2, h3, .brand-title { font-family: 'Space Grotesk', sans-serif !important; }
    .stApp { background: radial-gradient(circle at 15% 15%, #121829 0%, #080b12 100%); color: #f8fafc; }
    .hero-box {
        background: linear-gradient(135deg, rgba(99, 102, 241, 0.2), rgba(236, 72, 153, 0.2));
        border: 1.5px solid rgba(255, 255, 255, 0.15);
        border-radius: 18px; padding: 20px 28px; margin-bottom: 20px;
    }
    .hero-title {
        font-size: 2.2rem; font-weight: 800;
        background: linear-gradient(90deg, #38bdf8, #818cf8, #f472b6);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin: 0;
    }
    .status-card {
        border-radius: 16px; padding: 20px; margin-bottom: 20px;
        display: flex; align-items: center; gap: 16px;
    }
    .status-normal { background: rgba(16, 185, 129, 0.2); border: 2px solid #10b981; color: #ecfdf5; }
    .status-fall { background: rgba(239, 68, 68, 0.3); border: 2px solid #ef4444; color: #fef2f2; }
    .status-intrusion { background: rgba(245, 158, 11, 0.3); border: 2px solid #f59e0b; color: #fffbeb; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="hero-box">
    <div class="hero-title">AEGIS // SMART SAFETY MONITOR</div>
    <div style="color: #cbd5e1; margin-top: 4px;">Cloud Real-Time Fall & Perimeter Security Engine</div>
</div>
""", unsafe_allow_html=True)

st.sidebar.markdown("### 🎛️ **Feed Source**")
input_source = st.sidebar.radio("Select Source:", ("Cloud Live Camera (WebRTC)", "Upload Video File"))

@st.cache_resource
def load_model():
    return YOLO("yolov8n-pose.pt")

model = load_model()

# Debounce state for alerts
if "last_alert" not in st.session_state:
    st.session_state.last_alert = 0

def send_alert(message):
    curr = time.time()
    if curr - st.session_state.last_alert > 10:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
        try:
            requests.post(url, json=payload, timeout=2)
            st.session_state.last_alert = curr
        except Exception:
            pass

# Callback for WebRTC browser stream
def video_frame_callback(frame: av.VideoFrame) -> av.VideoFrame:
    img = frame.to_ndarray(format="bgr24")
    h, w, _ = img.shape
    
    # Perimeter
    zone_x1, zone_y1, zone_x2, zone_y2 = int(w * 0.6), int(h * 0.1), int(w * 0.95), int(h * 0.6)
    cv2.rectangle(img, (zone_x1, zone_y1), (zone_x2, zone_y2), (245, 158, 11), 2)
    cv2.putText(img, "RESTRICTED", (zone_x1 + 8, zone_y1 + 22), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (245, 158, 11), 2)

    results = model(img, conf=0.35, verbose=False)

    for result in results:
        boxes = result.boxes.xyxy.cpu().numpy() if result.boxes else []
        keypoints_all = result.keypoints.data.cpu().numpy() if result.keypoints is not None else []

        for idx, box in enumerate(boxes):
            bx1, by1, bx2, by2 = map(int, box[:4])
            box_w = bx2 - bx1
            box_h = by2 - by1
            cx, cy = (bx1 + bx2) // 2, (by1 + by2) // 2

            is_fall = box_w > (box_h * 0.95)
            if len(keypoints_all) > idx:
                kpts = keypoints_all[idx]
                if (kpts[5][2] > 0.3 or kpts[6][2] > 0.3) and (kpts[11][2] > 0.3 or kpts[12][2] > 0.3):
                    sy = np.mean([pt[1] for pt in [kpts[5], kpts[6]] if pt[2] > 0.3])
                    hy = np.mean([pt[1] for pt in [kpts[11], kpts[12]] if pt[2] > 0.3])
                    if abs(sy - hy) < 55:
                        is_fall = True

            if is_fall:
                cv2.rectangle(img, (bx1, by1), (bx2, by2), (239, 68, 68), 3)
                cv2.putText(img, "! FALL DETECTED !", (bx1, by1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (239, 68, 68), 2)
                send_alert(f"🚨 *AEGIS ALERT*\nFall Detected on Cloud Stream!\nTime: `{datetime.datetime.now().strftime('%H:%M:%S')}`")

            elif zone_x1 < cx < zone_x2 and zone_y1 < cy < zone_y2:
                cv2.rectangle(img, (bx1, by1), (bx2, by2), (245, 158, 11), 3)
                cv2.putText(img, "! INTRUSION !", (bx1, by1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (245, 158, 11), 2)
                send_alert(f"⚠️ *AEGIS SECURITY ALERT*\nRestricted Perimeter Breach!\nTime: `{datetime.datetime.now().strftime('%H:%M:%S')}`")

    annotated = results[0].plot() if results else img
    return av.VideoFrame.from_ndarray(annotated, format="bgr24")

# UI Routing
col_video, col_info = st.columns([1.7, 1.1])

if input_source == "Cloud Live Camera (WebRTC)":
    with col_video:
        webrtc_streamer(
            key="aegis-cam",
            mode=WebRtcMode.SENDRECV,
            rtc_configuration=RTC_CONFIG,
            video_frame_callback=video_frame_callback,
            media_stream_constraints={"video": True, "audio": False},
            async_processing=True
        )
    with col_info:
        st.markdown("""
        <div class="status-card status-normal">
            <div style="font-size: 2rem;">🟢</div>
            <div>
                <div style="font-weight: 800;">BROWSER CAMERA CONNECTED</div>
                <div style="font-size: 0.85rem; opacity: 0.9;">Click START on the video box to begin live streaming.</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

elif input_source == "Upload Video File":
    uploaded_file = st.sidebar.file_uploader("Upload CCTV Clip (.mp4, .avi, .mov)", type=["mp4", "avi", "mov"])
    if uploaded_file is not None:
        tfile = tempfile.NamedTemporaryFile(delete=False)
        tfile.write(uploaded_file.read())
        cap = cv2.VideoCapture(tfile.name)
        v_placeholder = col_video.empty()
        
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            results = model(frame, conf=0.35, verbose=False)
            annotated = results[0].plot() if results else frame
            v_placeholder.image(cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB), channels="RGB", use_container_width=True)
            time.sleep(0.01)
        cap.release()
