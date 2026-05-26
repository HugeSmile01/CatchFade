"""
CatchFade - Data Logger & Storage
Handles persistent storage of sensor readings, detection results, and briefings.
Uses SQLite (local edge storage) with optional JSON export.
"""

import sqlite3
import json
import os
import csv
import logging
import hashlib
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

DB_PATH = os.getenv("CATCHFADE_DB", "catchfade_data.db")


class DataLogger:
    """
    SQLite-backed data logger for CatchFade.
    Stores sensor readings, anomalies, detection results, and briefings.
    """

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()
        logger.info(f"DataLogger initialized | db={db_path}")

    def _init_schema(self):
        with self.conn:
            self.conn.executescript("""
                CREATE TABLE IF NOT EXISTS sensor_readings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    location_id TEXT,
                    temperature_c REAL,
                    salinity_ppt REAL,
                    dissolved_oxygen_mgl REAL,
                    turbidity_ntu REAL,
                    ph REAL,
                    depth_m REAL,
                    acoustic_activity REAL,
                    motion_detected INTEGER,
                    light_lux REAL,
                    raw_json TEXT,
                    payload_hash TEXT,
                    reading_complete INTEGER DEFAULT 1,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS detection_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    location_id TEXT,
                    overall_severity TEXT,
                    scarcity_score REAL,
                    stress_index REAL,
                    species_activity_low INTEGER,
                    habitat_stable INTEGER,
                    anomaly_count INTEGER,
                    summary TEXT,
                    raw_json TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS anomalies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    detection_id INTEGER,
                    timestamp TEXT,
                    stress_type TEXT,
                    severity TEXT,
                    parameter TEXT,
                    observed_value REAL,
                    expected_range TEXT,
                    description TEXT,
                    ecological_implication TEXT,
                    FOREIGN KEY(detection_id) REFERENCES detection_results(id)
                );

                CREATE TABLE IF NOT EXISTS briefings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    briefing_id TEXT UNIQUE,
                    timestamp TEXT,
                    location_id TEXT,
                    llm_provider TEXT,
                    ecological_status TEXT,
                    detailed_analysis TEXT,
                    species_risk_assessment TEXT,
                    recommended_actions TEXT,
                    confidence_note TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );

                CREATE INDEX IF NOT EXISTS idx_readings_ts ON sensor_readings(timestamp);
                CREATE INDEX IF NOT EXISTS idx_detections_severity ON detection_results(overall_severity);
            """)

        self._ensure_column("sensor_readings", "payload_hash", "TEXT")
        self._ensure_column("sensor_readings", "reading_complete", "INTEGER DEFAULT 1")

    def _ensure_column(self, table: str, column: str, definition: str):
        existing = {row[1] for row in self.conn.execute(f"PRAGMA table_info({table})").fetchall()}
        if column not in existing:
            self.conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
            self.conn.commit()

    def log_reading(self, reading) -> int:
        r = reading.to_dict()

        required_fields = [
            "timestamp", "location_id", "temperature_c", "salinity_ppt",
            "dissolved_oxygen_mgl", "turbidity_ntu", "ph", "depth_m",
            "acoustic_activity", "motion_detected", "light_lux"
        ]
        reading_complete = all(r.get(field) is not None for field in required_fields)

        canonical_payload = json.dumps(r, sort_keys=True, separators=(",", ":"))
        payload_hash = hashlib.sha256(canonical_payload.encode("utf-8")).hexdigest()

        cursor = self.conn.execute("""
            INSERT INTO sensor_readings 
            (timestamp, location_id, temperature_c, salinity_ppt, dissolved_oxygen_mgl,
             turbidity_ntu, ph, depth_m, acoustic_activity, motion_detected, light_lux, raw_json,
             payload_hash, reading_complete)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            r["timestamp"], r["location_id"], r["temperature_c"], r["salinity_ppt"],
            r["dissolved_oxygen_mgl"], r["turbidity_ntu"], r["ph"], r["depth_m"],
            r["acoustic_activity"], int(r["motion_detected"]), r["light_lux"],
            canonical_payload, payload_hash, int(reading_complete)
        ))
        self.conn.commit()
        return cursor.lastrowid

    def log_detection(self, result) -> int:
        cursor = self.conn.execute("""
            INSERT INTO detection_results
            (timestamp, location_id, overall_severity, scarcity_score, stress_index,
             species_activity_low, habitat_stable, anomaly_count, summary, raw_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            result.timestamp, result.location_id, result.overall_severity,
            result.scarcity_score, result.stress_index, int(result.species_activity_low),
            int(result.habitat_stable), len(result.anomalies), result.summary,
            result.to_json()
        ))
        detection_id = cursor.lastrowid

        for anomaly in result.anomalies:
            self.conn.execute("""
                INSERT INTO anomalies
                (detection_id, timestamp, stress_type, severity, parameter,
                 observed_value, expected_range, description, ecological_implication)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                detection_id, anomaly.timestamp, anomaly.stress_type, anomaly.severity,
                anomaly.parameter, anomaly.observed_value, anomaly.expected_range,
                anomaly.description, anomaly.ecological_implication
            ))

        self.conn.commit()
        return detection_id

    def log_briefing(self, briefing) -> int:
        cursor = self.conn.execute("""
            INSERT OR REPLACE INTO briefings
            (briefing_id, timestamp, location_id, llm_provider, ecological_status,
             detailed_analysis, species_risk_assessment, recommended_actions, confidence_note)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            briefing.briefing_id, briefing.timestamp, briefing.location_id,
            briefing.llm_provider, briefing.ecological_status, briefing.detailed_analysis,
            briefing.species_risk_assessment, briefing.recommended_actions, briefing.confidence_note
        ))
        self.conn.commit()
        return cursor.lastrowid

    def get_recent_readings(self, limit: int = 50) -> list:
        rows = self.conn.execute(
            "SELECT * FROM sensor_readings ORDER BY timestamp DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]

    def get_critical_events(self, limit: int = 20) -> list:
        rows = self.conn.execute("""
            SELECT * FROM detection_results 
            WHERE overall_severity IN ('CRITICAL', 'EMERGENCY')
            ORDER BY timestamp DESC LIMIT ?
        """, (limit,)).fetchall()
        return [dict(r) for r in rows]

    def get_scarcity_trend(self, location_id: str = None, limit: int = 100) -> list:
        query = "SELECT timestamp, scarcity_score, stress_index, overall_severity FROM detection_results"
        params = []
        if location_id:
            query += " WHERE location_id = ?"
            params.append(location_id)
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        rows = self.conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]

    def export_csv(self, output_path: str = "catchfade_export.csv"):
        rows = self.get_recent_readings(limit=10000)
        if not rows:
            logger.warning("No data to export.")
            return
        with open(output_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)
        logger.info(f"Exported {len(rows)} readings to {output_path}")

    def export_json(self, output_path: str = "catchfade_export.json"):
        rows = self.get_recent_readings(limit=10000)
        with open(output_path, "w") as f:
            json.dump(rows, f, indent=2)
        logger.info(f"Exported {len(rows)} readings to {output_path}")

    def get_stats(self) -> dict:
        stats = {}
        for table in ["sensor_readings", "detection_results", "anomalies", "briefings"]:
            count = self.conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            stats[table] = count
        critical = self.conn.execute(
            "SELECT COUNT(*) FROM detection_results WHERE overall_severity IN ('CRITICAL','EMERGENCY')"
        ).fetchone()[0]
        stats["critical_events"] = critical
        return stats

    def close(self):
        self.conn.close()


if __name__ == "__main__":
    import sys
    sys.path.insert(0, ".")
    from sensor_manager import SensorManager
    from anomaly_detector import AnomalyDetector

    logger.basicConfig(level=logging.INFO)
    db = DataLogger(":memory:")  # In-memory test
    manager = SensorManager(simulated=True)
    detector = AnomalyDetector()

    print("=== CatchFade DataLogger Test ===")
    for i in range(5):
        reading = manager.collect()
        result = detector.detect(reading)
        db.log_reading(reading)
        db.log_detection(result)

    stats = db.get_stats()
    print(f"Database stats: {json.dumps(stats, indent=2)}")
    print(f"\nCritical events: {db.get_critical_events()}")
