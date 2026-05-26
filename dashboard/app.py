"""
CatchFade - Web Dashboard (Flask)
Real-time monitoring dashboard accessible via browser.
Run: python dashboard/app.py
Access: http://localhost:5000
"""

import sys
import os
import json
import threading
import time
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../src"))

try:
    from flask import Flask, jsonify, render_template_string
except ImportError:
    print("Install Flask: pip install flask")
    sys.exit(1)

from sensor_manager import SensorManager
from anomaly_detector import AnomalyDetector
from briefing_generator import EcologicalBriefingGenerator
from data_logger import DataLogger

app = Flask(__name__)

# ─── Global State ──────────────────────────────────────────────────────────────
state = {
    "latest_reading": {},
    "latest_result": {},
    "latest_briefing": {},
    "history": [],
    "scarcity_trend": [],
    "running": False,
}

DEFAULT_READING = {
    "timestamp": None,
    "location_id": "--",
    "temperature_c": 0.0,
    "salinity_ppt": 0.0,
    "dissolved_oxygen_mgl": 0.0,
    "ph": 0.0,
    "turbidity_ntu": 0.0,
    "depth_m": 0.0,
    "acoustic_activity": 0.0,
    "motion_detected": False,
    "light_lux": 0.0,
}

DEFAULT_DETECTION = {
    "overall_severity": "NORMAL",
    "scarcity_score": 0.0,
    "stress_index": 0.0,
    "anomalies": [],
    "species_activity_low": False,
    "habitat_stable": True,
}

manager = SensorManager(simulated=True)
detector = AnomalyDetector()
generator = EcologicalBriefingGenerator(provider="mock")
db = DataLogger("catchfade_data.db")

# ─── Background Sensor Thread ──────────────────────────────────────────────────

def sensor_loop():
    count = 0
    while state["running"]:
        reading = manager.collect()
        result = detector.detect(reading)
        db.log_reading(reading)
        db.log_detection(result)

        count += 1
        briefing = None
        if count % 10 == 0 or result.overall_severity in ["CRITICAL", "EMERGENCY"]:
            briefing = generator.generate(result, reading)
            db.log_briefing(briefing)
            state["latest_briefing"] = briefing.to_dict()

        r = reading.to_dict()
        d = result.to_dict()

        state["latest_reading"] = r
        state["latest_result"] = d
        state["history"].append({**r, "severity": d["overall_severity"], "scarcity": d["scarcity_score"]})
        if len(state["history"]) > 100:
            state["history"] = state["history"][-100:]

        state["scarcity_trend"].append({
            "timestamp": r["timestamp"],
            "scarcity_score": d["scarcity_score"],
            "stress_index": d["stress_index"],
            "severity": d["overall_severity"],
        })
        if len(state["scarcity_trend"]) > 50:
            state["scarcity_trend"] = state["scarcity_trend"][-50:]

        time.sleep(5)

# ─── HTML Dashboard Template ───────────────────────────────────────────────────

DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>CatchFade — Marine Monitoring Dashboard</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Inter:wght@300;400;600&display=swap');
  :root {
    --bg: #0a0e1a; --panel: #111827; --border: #1f2937;
    --accent: #06b6d4; --warn: #f59e0b; --crit: #ef4444; --ok: #10b981;
    --text: #e2e8f0; --muted: #64748b;
  }
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { background: var(--bg); color: var(--text); font-family: 'Inter', sans-serif; min-height: 100vh; }
  header { background: var(--panel); border-bottom: 1px solid var(--border); padding: 16px 32px;
    display: flex; align-items: center; gap: 16px; }
  header h1 { font-family: 'Space Mono', monospace; font-size: 1.4rem; color: var(--accent); }
  header span { font-size: 0.8rem; color: var(--muted); }
  .status-dot { width: 10px; height: 10px; border-radius: 50%; background: var(--ok); animation: pulse 2s infinite; }
  @keyframes pulse { 0%,100% { opacity: 1; } 50% { opacity: 0.4; } }
  main { padding: 24px 32px; display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 16px; }
  .card { background: var(--panel); border: 1px solid var(--border); border-radius: 12px; padding: 20px; }
  .card h2 { font-family: 'Space Mono', monospace; font-size: 0.75rem; color: var(--muted); text-transform: uppercase; letter-spacing: 2px; margin-bottom: 16px; }
  .metric { display: flex; justify-content: space-between; align-items: center; padding: 8px 0; border-bottom: 1px solid var(--border); }
  .metric:last-child { border-bottom: none; }
  .metric-label { font-size: 0.85rem; color: var(--muted); }
  .metric-value { font-family: 'Space Mono', monospace; font-size: 1rem; font-weight: 700; }
  .val-ok { color: var(--ok); } .val-warn { color: var(--warn); } .val-crit { color: var(--crit); }
  .severity-badge { padding: 4px 12px; border-radius: 20px; font-size: 0.75rem; font-family: 'Space Mono', monospace; font-weight: 700; }
  .sev-NORMAL { background: rgba(16,185,129,0.15); color: var(--ok); }
  .sev-WARNING { background: rgba(245,158,11,0.15); color: var(--warn); }
  .sev-CRITICAL { background: rgba(239,68,68,0.15); color: var(--crit); }
  .sev-EMERGENCY { background: rgba(239,68,68,0.3); color: var(--crit); animation: pulse 1s infinite; }
  .scarcity-bar { height: 10px; background: var(--border); border-radius: 5px; margin: 12px 0; overflow: hidden; }
  .scarcity-fill { height: 100%; border-radius: 5px; transition: width 1s, background 1s; }
  .anomaly-item { padding: 10px; background: rgba(239,68,68,0.1); border-left: 3px solid var(--crit); border-radius: 4px; margin: 6px 0; font-size: 0.8rem; }
  .briefing-text { font-size: 0.82rem; line-height: 1.7; color: #94a3b8; white-space: pre-wrap; max-height: 200px; overflow-y: auto; }
  .trend-row { display: flex; align-items: center; gap: 8px; padding: 4px 0; font-size: 0.78rem; font-family: 'Space Mono', monospace; }
  .full-width { grid-column: 1 / -1; }
  footer { text-align: center; padding: 20px; color: var(--muted); font-size: 0.75rem; font-family: 'Space Mono', monospace; }
</style>
</head>
<body>
<header>
  <div class="status-dot" id="dot"></div>
  <h1>⚓ CatchFade</h1>
  <span>Coastal Marine Scarcity Detection System</span>
  <span style="margin-left:auto;font-family:'Space Mono',monospace;font-size:0.75rem" id="ts">--</span>
</header>
<main id="main">
  <div class="card">
    <h2>System Status</h2>
    <div class="metric"><span class="metric-label">Severity</span><span id="severity" class="severity-badge sev-NORMAL">NORMAL</span></div>
    <div class="metric"><span class="metric-label">Scarcity Score</span><span id="scarcity" class="metric-value val-ok">0.00</span></div>
    <div class="scarcity-bar"><div class="scarcity-fill" id="scarcity-bar" style="width:0%;background:var(--ok)"></div></div>
    <div class="metric"><span class="metric-label">Stress Index</span><span id="stress" class="metric-value">0.00</span></div>
    <div class="metric"><span class="metric-label">Species Activity</span><span id="species" class="metric-value">--</span></div>
    <div class="metric"><span class="metric-label">Habitat Stable</span><span id="habitat" class="metric-value">--</span></div>
  </div>

  <div class="card">
    <h2>Water Quality</h2>
    <div class="metric"><span class="metric-label">Temperature (°C)</span><span id="temp" class="metric-value">--</span></div>
    <div class="metric"><span class="metric-label">Salinity (ppt)</span><span id="sal" class="metric-value">--</span></div>
    <div class="metric"><span class="metric-label">Dissolved O₂ (mg/L)</span><span id="do" class="metric-value">--</span></div>
    <div class="metric"><span class="metric-label">pH</span><span id="ph" class="metric-value">--</span></div>
    <div class="metric"><span class="metric-label">Turbidity (NTU)</span><span id="turb" class="metric-value">--</span></div>
    <div class="metric"><span class="metric-label">Depth (m)</span><span id="depth" class="metric-value">--</span></div>
  </div>

  <div class="card">
    <h2>Biological Indicators</h2>
    <div class="metric"><span class="metric-label">Acoustic Activity</span><span id="acoustic" class="metric-value">--</span></div>
    <div class="metric"><span class="metric-label">Motion Detected</span><span id="motion" class="metric-value">--</span></div>
    <div class="metric"><span class="metric-label">Ambient Light (lux)</span><span id="light" class="metric-value">--</span></div>
    <div class="metric"><span class="metric-label">Node ID</span><span id="node" class="metric-value" style="font-size:0.7rem">--</span></div>
  </div>

  <div class="card">
    <h2>Anomalies</h2>
    <div id="anomalies"><span style="color:var(--muted);font-size:0.82rem">No anomalies detected.</span></div>
  </div>

  <div class="card full-width">
    <h2>Latest Ecological Briefing</h2>
    <div class="briefing-text" id="briefing">Waiting for first briefing generation...</div>
  </div>

  <div class="card full-width">
    <h2>Scarcity Trend (Last 20 Readings)</h2>
    <div id="trend"></div>
  </div>
</main>
<footer>CatchFade v1.0 · Auto-refreshing every 5s · Coastal Marine Monitoring System</footer>

<script>
function sevColor(s) {
  return s === 'NORMAL' ? 'var(--ok)' : s === 'WARNING' ? 'var(--warn)' : 'var(--crit)';
}
function valClass(v, low, high) {
  if (v < low || v > high) return 'val-crit';
  return 'val-ok';
}

async function refresh() {
  try {
    const [statusRes, histRes, briefRes] = await Promise.all([
      fetch('/api/status'), fetch('/api/history'), fetch('/api/briefing')
    ]);
    const status = await statusRes.json();
    const hist = await histRes.json();
    const brief = await briefRes.json();

    const r = status.reading || {};
    const d = status.detection || {};
    if (!Object.keys(r).length || !Object.keys(d).length) {
      document.getElementById('ts').textContent = new Date().toLocaleTimeString();
      return;
    }
    const sev = d.overall_severity;

    document.getElementById('ts').textContent = new Date().toLocaleTimeString();
    document.getElementById('severity').textContent = sev;
    document.getElementById('severity').className = 'severity-badge sev-' + sev;

    const sc = parseFloat(d.scarcity_score);
    document.getElementById('scarcity').textContent = sc.toFixed(2);
    document.getElementById('scarcity').className = 'metric-value ' + (sc < 0.3 ? 'val-ok' : sc < 0.6 ? 'val-warn' : 'val-crit');
    const bar = document.getElementById('scarcity-bar');
    bar.style.width = (sc * 100) + '%';
    bar.style.background = sc < 0.3 ? 'var(--ok)' : sc < 0.6 ? 'var(--warn)' : 'var(--crit)';

    document.getElementById('stress').textContent = parseFloat(d.stress_index).toFixed(2);
    document.getElementById('species').textContent = d.species_activity_low ? '⚠ Low' : '✓ Active';
    document.getElementById('species').className = 'metric-value ' + (d.species_activity_low ? 'val-warn' : 'val-ok');
    document.getElementById('habitat').textContent = d.habitat_stable ? '✓ Stable' : '⚠ Stressed';
    document.getElementById('habitat').className = 'metric-value ' + (d.habitat_stable ? 'val-ok' : 'val-warn');

    document.getElementById('temp').textContent = r.temperature_c + ' °C';
    document.getElementById('sal').textContent = r.salinity_ppt + ' ppt';
    document.getElementById('do').textContent = r.dissolved_oxygen_mgl + ' mg/L';
    document.getElementById('do').className = 'metric-value ' + (r.dissolved_oxygen_mgl < 3 ? 'val-crit' : r.dissolved_oxygen_mgl < 5 ? 'val-warn' : 'val-ok');
    document.getElementById('ph').textContent = r.ph;
    document.getElementById('turb').textContent = r.turbidity_ntu + ' NTU';
    document.getElementById('depth').textContent = r.depth_m + ' m';
    document.getElementById('acoustic').textContent = r.acoustic_activity;
    document.getElementById('acoustic').className = 'metric-value ' + (r.acoustic_activity < 0.1 ? 'val-crit' : r.acoustic_activity < 0.2 ? 'val-warn' : 'val-ok');
    document.getElementById('motion').textContent = r.motion_detected ? '✓ Yes' : '✗ None';
    document.getElementById('light').textContent = r.light_lux;
    document.getElementById('node').textContent = r.location_id;

    const anomDiv = document.getElementById('anomalies');
    if (d.anomalies && d.anomalies.length > 0) {
      anomDiv.innerHTML = d.anomalies.map(a =>
        `<div class="anomaly-item"><strong>[${a.severity}] ${a.stress_type}</strong><br>${a.description}</div>`
      ).join('');
    } else {
      anomDiv.innerHTML = '<span style="color:var(--ok);font-size:0.82rem">✓ No anomalies detected.</span>';
    }

    if (brief.ecological_status) {
      document.getElementById('briefing').textContent =
        '[ ' + brief.briefing_id + ' | ' + brief.llm_provider + ' ]\n\n' +
        'STATUS: ' + brief.ecological_status + '\n\n' +
        brief.detailed_analysis;
    }

    const trendDiv = document.getElementById('trend');
    if (hist.length > 0) {
      const last20 = hist.slice(-20);
      trendDiv.innerHTML = last20.map((h, i) => {
        const bar = '█'.repeat(Math.round((h.scarcity || 0) * 20));
        const color = h.severity === 'NORMAL' ? 'var(--ok)' : h.severity === 'WARNING' ? 'var(--warn)' : 'var(--crit)';
        return `<div class="trend-row"><span style="color:var(--muted);width:30px">${i+1}</span><span style="color:${color};width:120px">${(h.scarcity||0).toFixed(2)}</span><span style="color:${color}">${bar}</span><span style="color:var(--muted);margin-left:8px">${h.severity}</span></div>`;
      }).join('');
    }

  } catch (e) {
    console.error('Refresh failed:', e);
  }
}

setInterval(refresh, 5000);
refresh();
</script>
</body>
</html>
"""

# ─── API Routes ────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template_string(DASHBOARD_HTML)

@app.route("/api/status")
def api_status():
    reading = state["latest_reading"] if state["latest_reading"] else DEFAULT_READING
    detection = state["latest_result"] if state["latest_result"] else DEFAULT_DETECTION
    return jsonify({
        "reading": reading,
        "detection": detection,
        "has_live_data": bool(state["latest_reading"] and state["latest_result"]),
    })

@app.route("/api/history")
def api_history():
    return jsonify(state["scarcity_trend"][-20:])

@app.route("/api/briefing")
def api_briefing():
    return jsonify(state["latest_briefing"])

@app.route("/api/stats")
def api_stats():
    return jsonify(db.get_stats())

@app.route("/api/health")
def api_health():
    return jsonify({
        "status": "ok",
        "sensor_loop_running": state["running"],
        "samples_captured": len(state["history"]),
        "last_update": state["latest_reading"].get("timestamp") if state["latest_reading"] else None,
    })

# ─── Entry Point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    state["running"] = True
    t = threading.Thread(target=sensor_loop, daemon=True)
    t.start()
    print("\n╔══════════════════════════════════════════╗")
    print("║  CatchFade Dashboard                     ║")
    print("║  Open: http://localhost:5000             ║")
    print("╚══════════════════════════════════════════╝\n")
    app.run(host="0.0.0.0", port=5000, debug=False)
