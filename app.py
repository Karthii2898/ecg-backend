from flask import Flask, jsonify
from flask_cors import CORS
import math
import random
import time
import os

app = Flask(__name__)
CORS(app)

t = 0

def generate_ecg():
    global t
    base = 1.65
    noise = random.uniform(-0.03, 0.03)
    p = math.sin(t) * 0.05
    qrs = math.exp(-((t % 6) - 3) ** 2) * 1.2
    t += 0.25
    return base + p + qrs + noise

@app.route("/api/ecg/latest", methods=["GET"])
def get_latest_ecg():
    voltage = []

    for _ in range(20):
        v = generate_ecg()
        voltage.append(round(v, 3))

    return jsonify({
        "timestamp": int(time.time() * 1000),
        "voltage": voltage,
        "bpm": random.randint(70, 78)
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
