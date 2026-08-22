# 🛡️ AEGIS - AI Smart CCTV Anomaly & Safety Monitor

AEGIS is an edge-AI surveillance system that upgrades standard CCTV streams into active life-safety monitors. Using YOLOv8 Pose estimation and OpenCV, it analyzes 17 skeletal keypoints in real time to detect human falls, medical collapses, and unauthorized perimeter breaches, automatically dispatching instant alerts via Telegram.

## 🚀 Key Features
- **Human Skeletal Kinematics:** Tracks 17 body keypoints using YOLOv8-Pose to prevent false triggers from pets or dropped objects.
- **Biomechanical Fall Detection:** Evaluates torso compression and aspect ratios to identify sudden collapses.
- **Perimeter Intrusion Detection:** Monitored virtual boundary zones with centroid tracking.
- **Automated Dispatch:** Integrated Telegram Bot API triggers mobile push notifications in under 1 second.
- **Clean Neon UI:** High-contrast dashboard with Google Fonts (Plus Jakarta Sans & Space Grotesk).

## 🛠️ Tech Stack
- **AI / Computer Vision:** Ultralytics YOLOv8-Pose, OpenCV
- **UI Framework:** Streamlit, Custom CSS (Google Fonts)
- **Alert Dispatch:** Telegram Bot API (HTTP Requests)
- **Language:** Python 3.9+

## ⚙️ Quick Start

1. **Clone the repository:**
   ```bash
   git clone [https://github.com/reshevk/smart-cctv-anomaly-detector.git](https://github.com/reshevk/smart-cctv-anomaly-detector.git)
   cd smart-cctv-anomaly-detector
