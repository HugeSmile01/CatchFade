"""
CatchFade - Main Pipeline Orchestrator
Self-operating aquatic scarcity detection system.
Runs the full pipeline: Sense → Detect → Analyze → Brief → Store → Alert
"""

import time
import signal
import logging
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.dirname(__file__))

from sensor_manager import SensorManager
from anomaly_detector import AnomalyDetector, SeverityLevel
from briefing_generator import EcologicalBriefingGenerator
from data_logger import DataLogger

# ─── Logging Setup ─────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("catchfade.log", encoding="utf-8"),
    ]
)
logger = logging.getLogger("CatchFade.Main")


# ─── Configuration ─────────────────────────────────────────────────────────────

CONFIG = {
    # Sensing
    "node_id": os.getenv("CF_NODE_ID", "CF-NODE-COASTAL-01"),
    "simulated": os.getenv("CF_SIMULATED", "true").lower() == "true",
    "sense_interval_sec": float(os.getenv("CF_SENSE_INTERVAL", "30")),

    # LLM Briefing
    "llm_provider": os.getenv("CF_LLM_PROVIDER", "mock"),      # mock | anthropic | openai | ollama
    "llm_model": os.getenv("CF_LLM_MODEL", "claude-sonnet-4-20250514"),
    "briefing_every_n_readings": int(os.getenv("CF_BRIEFING_INTERVAL", "10")),  # Generate briefing every N readings
    "briefing_on_critical": True,                                                 # Always brief on CRITICAL+

    # Storage
    "db_path": os.getenv("CF_DB_PATH", "catchfade_data.db"),

    # Alerts
    "alert_severity_threshold": os.getenv("CF_ALERT_THRESHOLD", "WARNING"),
    "scarcity_alert_threshold": float(os.getenv("CF_SCARCITY_THRESHOLD", "0.5")),
}


# ─── Alert System ──────────────────────────────────────────────────────────────

class AlertSystem:
    """Simple alert dispatcher. Extend with email/SMS/webhook as needed."""

    def alert(self, result, briefing=None):
        severity = result.overall_severity
        score = result.scarcity_score
        location = result.location_id

        msg = (
            f"\n{'='*60}\n"
            f"🚨 CATCHFADE ALERT — {severity}\n"
            f"Location  : {location}\n"
            f"Timestamp : {result.timestamp}\n"
            f"Scarcity  : {score:.2f}/1.00\n"
            f"Stress    : {result.stress_index:.1f}/10\n"
            f"Anomalies : {len(result.anomalies)}\n"
        )
        for a in result.anomalies:
            msg += f"  [{a.severity}] {a.stress_type} — {a.parameter}={a.observed_value}\n"

        if briefing:
            msg += f"\nECOLOGICAL STATUS: {briefing.ecological_status}\n"

        msg += "="*60

        # Log alert (extend here for email/webhook/SMS)
        logger.warning(msg)
        print(msg)

        # TODO: Add your alert channel here:
        # self._send_email(msg)
        # self._post_webhook(msg)
        # self._send_sms(msg)


# ─── Main Pipeline ─────────────────────────────────────────────────────────────

class CatchFadePipeline:
    """
    The main self-operating pipeline.
    Runs continuously until stopped (Ctrl+C or SIGTERM).
    """

    def __init__(self, config: dict = CONFIG):
        self.config = config
        self.running = False
        self.reading_count = 0
        self.briefing_count = 0

        logger.info("Initializing CatchFade pipeline...")
        logger.info(f"Config: {json.dumps(config, indent=2)}")

        # Initialize components
        self.sensor_manager = SensorManager(
            location_id=config["node_id"],
            simulated=config["simulated"]
        )
        self.detector = AnomalyDetector()
        self.briefing_generator = EcologicalBriefingGenerator(
            provider=config["llm_provider"],
            model=config.get("llm_model", "claude-sonnet-4-20250514") if config["llm_provider"] == "anthropic" else None
        )
        self.db = DataLogger(config["db_path"])
        self.alert_system = AlertSystem()

        # Handle graceful shutdown
        signal.signal(signal.SIGTERM, self._shutdown)
        signal.signal(signal.SIGINT, self._shutdown)

        logger.info("CatchFade pipeline initialized. Ready.")

    def _shutdown(self, *args):
        logger.info("Shutdown signal received. Stopping pipeline...")
        self.running = False

    def _should_generate_briefing(self, result) -> bool:
        """Determine if this cycle should generate an LLM briefing."""
        if self.config["briefing_on_critical"] and result.overall_severity in [
            SeverityLevel.CRITICAL.value, SeverityLevel.EMERGENCY.value
        ]:
            return True
        if self.reading_count % self.config["briefing_every_n_readings"] == 0:
            return True
        return False

    def _should_alert(self, result) -> bool:
        severity_order = {
            SeverityLevel.NORMAL.value: 0,
            SeverityLevel.WARNING.value: 1,
            SeverityLevel.CRITICAL.value: 2,
            SeverityLevel.EMERGENCY.value: 3,
        }
        threshold = self.config["alert_severity_threshold"]
        result_level = severity_order.get(result.overall_severity, 0)
        threshold_level = severity_order.get(threshold, 1)
        if result_level >= threshold_level:
            return True
        if result.scarcity_score >= self.config["scarcity_alert_threshold"]:
            return True
        return False

    def run_once(self) -> dict:
        """Execute a single pipeline cycle."""
        self.reading_count += 1
        cycle_start = time.time()

        logger.info(f"─── Cycle #{self.reading_count} ───────────────────────")

        # Step 1: Sense
        reading = self.sensor_manager.collect()
        reading_id = self.db.log_reading(reading)
        logger.info(f"Sensor reading collected | id={reading_id}")

        # Step 2: Detect
        result = self.detector.detect(reading)
        detection_id = self.db.log_detection(result)
        logger.info(
            f"Detection complete | severity={result.overall_severity} | "
            f"scarcity={result.scarcity_score:.2f} | anomalies={len(result.anomalies)}"
        )

        # Step 3: Briefing (conditional)
        briefing = None
        if self._should_generate_briefing(result):
            briefing = self.briefing_generator.generate(result, reading)
            self.db.log_briefing(briefing)
            self.briefing_count += 1
            logger.info(f"Briefing generated | id={briefing.briefing_id}")
            print(briefing.to_report_text())

        # Step 4: Alert (conditional)
        if self._should_alert(result):
            self.alert_system.alert(result, briefing)

        elapsed = round(time.time() - cycle_start, 2)
        logger.info(f"Cycle #{self.reading_count} complete in {elapsed}s")

        return {
            "cycle": self.reading_count,
            "reading_id": reading_id,
            "detection_id": detection_id,
            "severity": result.overall_severity,
            "scarcity_score": result.scarcity_score,
            "briefing_generated": briefing is not None,
            "elapsed_sec": elapsed,
        }

    def run(self, max_cycles: int = None):
        """Run the pipeline continuously."""
        self.running = True
        logger.info(
            f"\n{'='*60}\n"
            f"  CATCHFADE SYSTEM STARTING\n"
            f"  Node     : {self.config['node_id']}\n"
            f"  Mode     : {'SIMULATED' if self.config['simulated'] else 'HARDWARE'}\n"
            f"  Interval : {self.config['sense_interval_sec']}s\n"
            f"  LLM      : {self.config['llm_provider']}\n"
            f"{'='*60}"
        )

        try:
            while self.running:
                if max_cycles and self.reading_count >= max_cycles:
                    logger.info(f"Max cycles ({max_cycles}) reached. Stopping.")
                    break

                cycle_result = self.run_once()

                if self.running and (not max_cycles or self.reading_count < max_cycles):
                    logger.info(f"Next reading in {self.config['sense_interval_sec']}s...")
                    time.sleep(self.config["sense_interval_sec"])

        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received.")
        finally:
            self._cleanup()

    def _cleanup(self):
        stats = self.db.get_stats()
        logger.info(f"\nCatchFade shutdown. Final stats: {json.dumps(stats, indent=2)}")
        self.db.close()
        logger.info("Pipeline stopped cleanly.")


# ─── Entry Point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="CatchFade — Marine Scarcity Detection System")
    parser.add_argument("--simulated", action="store_true", default=True, help="Use simulated sensors")
    parser.add_argument("--hardware", action="store_true", help="Use real hardware sensors")
    parser.add_argument("--llm", choices=["mock", "anthropic", "openai", "ollama"], default="mock")
    parser.add_argument("--interval", type=float, default=5.0, help="Sensing interval in seconds")
    parser.add_argument("--cycles", type=int, default=None, help="Max cycles (None = run forever)")
    parser.add_argument("--node", type=str, default="CF-NODE-COASTAL-01")
    args = parser.parse_args()

    CONFIG.update({
        "simulated": not args.hardware,
        "llm_provider": args.llm,
        "sense_interval_sec": args.interval,
        "node_id": args.node,
    })

    pipeline = CatchFadePipeline(CONFIG)
    pipeline.run(max_cycles=args.cycles)
