from flask import Flask, request, jsonify
from flask_cors import CORS
import time
import threading
from collections import deque

app = Flask(__name__)
CORS(app)

# ================= CONFIG =================
MAX_BUFFER = 1000
OFFLINE_TIMEOUT = 5            # seconds
R_PEAK_THRESHOLD = 2.0         # adjust if needed
MIN_RR_INTERVAL = 0.3          # seconds (max 200 BPM)
MAX_RR_INTERVAL = 2.0          # seconds (min 30 BPM)

# ================= STORAGE =================
ecg_buffer = deque(maxlen=MAX_BUFFER)
r_peaks = deque(maxlen=10)     # store timestamps of R-peaks
last_update_time = 0
last_voltage = 0
lock = threading.Lock()

# ================= BPM LOGIC =================
def calculate_bpm():
    if len(r_peaks) < 2:
        return None

    rr_intervals = [
        r_peaks[i] - r_peaks[i - 1]
        for i in range(1, len(r_peaks))
    ]

    # filter unrealistic intervals
    rr_intervals = [
        rr for rr in rr_intervals
        if MIN_RR_INTERVAL <= rr <= MAX_RR_INTERVAL
    ]

    if not rr_intervals:
        return None

    avg_rr = sum(rr_intervals) / len(rr_intervals)
    bpm = int(60 / avg_rr)
    return bpm

# ================= ESP32 POST =================
@app.route("/api/ecg", methods=["POST"])
def receive_ecg():
    global last_update_time, last_voltage

    data = request.get_json()
    if not data or "voltage" not in data:
        return jsonify({"error": "Invalid payload"}), 400

    voltage = float(data["voltage"])
    now = time.time()

    with lock:
        ecg_buffer.append(voltage)
        last_update_time = now

        # R-peak detection (rising edge + threshold)
        if (
            voltage > R_PEAK_THRESHOLD
            and last_voltage <= R_PEAK_THRESHOLD
        ):
            r_peaks.append(now)

        last_voltage = voltage

    return jsonify({"status": "ok"}), 200

# ================= FRONTEND GET =================
@app.route("/api/ecg/latest", methods=["GET"])
def get_latest_ecg():
    now = time.time()

    with lock:
        is_online = (now - last_update_time) < OFFLINE_TIMEOUT
        voltage_data = list(ecg_buffer)[-20:] if is_online else []
        bpm = calculate_bpm() if is_online else None

    return jsonify({
        "timestamp": int(now * 1000),
        "voltage": voltage_data,
        "bpm": bpm,
        "device_online": is_online
    })

# ================= HEALTH CHECK =================
@app.route("/")
def home():
    return "ECG Backend Running (Real BPM)", 200

# ================= RUN =================
if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
