"""
CatchFade - Anomaly & Scarcity Detection Engine
Detects ecological stress, species decline signals, and habitat anomalies
from sensor readings using rule-based thresholds + statistical analysis.
"""

import json
import logging
import statistics
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional
from enum import Enum

logger = logging.getLogger(__name__)

# ─── Enums ─────────────────────────────────────────────────────────────────────

class SeverityLevel(str, Enum):
    NORMAL = "NORMAL"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"
    EMERGENCY = "EMERGENCY"

class StressType(str, Enum):
    THERMAL_STRESS = "Thermal Stress"
    HYPOXIA = "Hypoxia (Low Dissolved Oxygen)"
    ACIDIFICATION = "Ocean Acidification"
    SALINITY_ANOMALY = "Salinity Anomaly"
    TURBIDITY_SPIKE = "Turbidity Spike"
    ACOUSTIC_SILENCE = "Acoustic Silence (Species Absence)"
    ACOUSTIC_SPIKE = "Acoustic Disturbance"
    MULTI_PARAMETER = "Multi-Parameter Stress Event"


# ─── Data Models ───────────────────────────────────────────────────────────────

@dataclass
class Anomaly:
    timestamp: str
    stress_type: str
    severity: str
    parameter: str
    observed_value: float
    expected_range: str
    description: str
    ecological_implication: str

    def to_dict(self):
        return asdict(self)


@dataclass
class DetectionResult:
    timestamp: str
    location_id: str
    anomalies: List[Anomaly] = field(default_factory=list)
    overall_severity: str = SeverityLevel.NORMAL
    scarcity_score: float = 0.0          # 0.0 (healthy) to 1.0 (severe scarcity)
    stress_index: float = 0.0            # Composite ecological stress index
    species_activity_low: bool = False
    habitat_stable: bool = True
    summary: str = ""

    def to_dict(self):
        d = asdict(self)
        return d

    def to_json(self):
        return json.dumps(self.to_dict(), indent=2)

    @property
    def has_anomalies(self):
        return len(self.anomalies) > 0


# ─── Thresholds ─────────────────────────────────────────────────────────────────

THRESHOLDS = {
    "temperature_c": {
        "warn_low": 18.0, "warn_high": 31.0,
        "crit_low": 15.0, "crit_high": 34.0,
        "stress_type": StressType.THERMAL_STRESS,
        "eco_impact": "Elevated temperature causes coral bleaching and fish mortality. Low temperature signals cold upwelling stress."
    },
    "dissolved_oxygen_mgl": {
        "warn_low": 5.0, "warn_high": 11.0,
        "crit_low": 3.0, "crit_high": 14.0,
        "stress_type": StressType.HYPOXIA,
        "eco_impact": "DO below 3 mg/L induces hypoxic stress in fish and invertebrates, causing mass mortality and species flight."
    },
    "ph": {
        "warn_low": 7.8, "warn_high": 8.3,
        "crit_low": 7.4, "crit_high": 8.6,
        "stress_type": StressType.ACIDIFICATION,
        "eco_impact": "pH drop indicates ocean acidification, impairing shell formation in mollusks and coral calcification."
    },
    "salinity_ppt": {
        "warn_low": 30.0, "warn_high": 37.0,
        "crit_low": 25.0, "crit_high": 42.0,
        "stress_type": StressType.SALINITY_ANOMALY,
        "eco_impact": "Salinity deviation disrupts osmoregulation in marine organisms, leading to physiological stress and relocation."
    },
    "turbidity_ntu": {
        "warn_low": None, "warn_high": 15.0,
        "crit_low": None, "crit_high": 40.0,
        "stress_type": StressType.TURBIDITY_SPIKE,
        "eco_impact": "High turbidity reduces light penetration, suppressing photosynthesis and disrupting visual predators."
    },
    "acoustic_activity": {
        "warn_low": 0.15, "warn_high": 0.9,
        "crit_low": 0.05, "crit_high": 1.0,
        "stress_type": StressType.ACOUSTIC_SILENCE,
        "eco_impact": "Acoustic silence is a strong indicator of species absence or displacement. Marine species produce consistent bioacoustic signals."
    },
}


# ─── Detector Engine ───────────────────────────────────────────────────────────

class AnomalyDetector:
    """
    Rule-based anomaly detector for CatchFade.
    Evaluates each sensor reading against marine thresholds and produces
    a structured DetectionResult with scarcity scoring.
    """

    def __init__(self):
        self.history: List[dict] = []   # Rolling window of past readings
        self.window_size = 20
        logger.info("AnomalyDetector initialized.")

    def _check_parameter(
        self,
        param: str,
        value: float,
        config: dict,
        timestamp: str
    ) -> Optional[Anomaly]:
        severity = None
        direction = ""

        if config["crit_low"] and value <= config["crit_low"]:
            severity = SeverityLevel.CRITICAL
            direction = f"critically low ({value} ≤ {config['crit_low']})"
        elif config["crit_high"] and value >= config["crit_high"]:
            severity = SeverityLevel.CRITICAL
            direction = f"critically high ({value} ≥ {config['crit_high']})"
        elif config["warn_low"] and value <= config["warn_low"]:
            severity = SeverityLevel.WARNING
            direction = f"below normal range ({value} ≤ {config['warn_low']})"
        elif config["warn_high"] and value >= config["warn_high"]:
            severity = SeverityLevel.WARNING
            direction = f"above normal range ({value} ≥ {config['warn_high']})"

        if severity:
            warn_low = config['warn_low'] or "N/A"
            warn_high = config['warn_high'] or "N/A"
            return Anomaly(
                timestamp=timestamp,
                stress_type=config["stress_type"].value,
                severity=severity.value,
                parameter=param,
                observed_value=value,
                expected_range=f"{warn_low} – {warn_high}",
                description=f"{param.replace('_', ' ').title()} is {direction}.",
                ecological_implication=config["eco_impact"]
            )
        return None

    def _compute_scarcity_score(self, anomalies: List[Anomaly]) -> float:
        """
        Composite score: 0.0 = healthy ecosystem, 1.0 = severe scarcity detected.
        Weighted by severity and number of concurrent stressors.
        """
        if not anomalies:
            return 0.0

        severity_weights = {
            SeverityLevel.WARNING.value: 0.25,
            SeverityLevel.CRITICAL.value: 0.6,
            SeverityLevel.EMERGENCY.value: 1.0,
        }

        total = sum(severity_weights.get(a.severity, 0) for a in anomalies)
        # Multi-stressor amplification
        if len(anomalies) >= 3:
            total *= 1.3
        return min(round(total, 3), 1.0)

    def _compute_stress_index(self, reading: dict) -> float:
        """Normalized composite stress index (0–10 scale)."""
        scores = []
        for param, config in THRESHOLDS.items():
            val = reading.get(param)
            if val is None:
                continue
            midpoint = ((config.get("warn_low") or 0) + (config.get("warn_high") or 0)) / 2
            spread = ((config.get("warn_high") or midpoint) - (config.get("warn_low") or midpoint)) / 2
            if spread > 0:
                deviation = abs(val - midpoint) / spread
                scores.append(min(deviation, 2.0))
        if not scores:
            return 0.0
        return round(min(statistics.mean(scores) * 5, 10.0), 2)

    def detect(self, reading) -> DetectionResult:
        """Run full anomaly detection on a SensorReading."""
        r = reading.to_dict()
        timestamp = r["timestamp"]
        location_id = r["location_id"]

        # Store in history
        self.history.append(r)
        if len(self.history) > self.window_size:
            self.history.pop(0)

        anomalies = []
        for param, config in THRESHOLDS.items():
            value = r.get(param)
            if value is None:
                continue
            anomaly = self._check_parameter(param, value, config, timestamp)
            if anomaly:
                anomalies.append(anomaly)

        # Upgrade severity if acoustic silence co-occurs with other stressors
        acoustic_anomaly = next((a for a in anomalies if a.parameter == "acoustic_activity"), None)
        if acoustic_anomaly and len(anomalies) >= 2:
            acoustic_anomaly.severity = SeverityLevel.EMERGENCY.value
            acoustic_anomaly.stress_type = StressType.MULTI_PARAMETER.value

        scarcity_score = self._compute_scarcity_score(anomalies)
        stress_index = self._compute_stress_index(r)

        # Determine overall severity
        severities = [a.severity for a in anomalies]
        if SeverityLevel.EMERGENCY.value in severities:
            overall = SeverityLevel.EMERGENCY
        elif SeverityLevel.CRITICAL.value in severities:
            overall = SeverityLevel.CRITICAL
        elif SeverityLevel.WARNING.value in severities:
            overall = SeverityLevel.WARNING
        else:
            overall = SeverityLevel.NORMAL

        species_low = r.get("acoustic_activity", 1.0) < 0.15 or not r.get("motion_detected", True)
        habitat_stable = overall in [SeverityLevel.NORMAL, SeverityLevel.WARNING]

        summary = self._generate_summary(anomalies, scarcity_score, overall)

        result = DetectionResult(
            timestamp=timestamp,
            location_id=location_id,
            anomalies=anomalies,
            overall_severity=overall.value,
            scarcity_score=scarcity_score,
            stress_index=stress_index,
            species_activity_low=species_low,
            habitat_stable=habitat_stable,
            summary=summary,
        )

        if anomalies:
            logger.warning(f"[{location_id}] {len(anomalies)} anomalies | severity={overall.value} | scarcity={scarcity_score}")
        else:
            logger.info(f"[{location_id}] No anomalies detected | stress_index={stress_index}")

        return result

    def _generate_summary(self, anomalies, scarcity_score, overall) -> str:
        if not anomalies:
            return "All parameters within normal marine baseline. Ecosystem appears stable."
        types = list(set(a.stress_type for a in anomalies))
        return (
            f"{len(anomalies)} anomaly/anomalies detected: {', '.join(types)}. "
            f"Overall severity: {overall.value}. "
            f"Scarcity score: {scarcity_score:.2f}/1.00. "
            f"{'Immediate ecological attention recommended.' if overall in [SeverityLevel.CRITICAL, SeverityLevel.EMERGENCY] else 'Monitor closely.'}"
        )


# ─── Entry Point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from sensor_manager import SensorManager

    manager = SensorManager(simulated=True)
    detector = AnomalyDetector()

    print("=== CatchFade Detection Engine Test ===\n")
    for i in range(5):
        reading = manager.collect()
        result = detector.detect(reading)
        print(f"Reading {i+1}: severity={result.overall_severity} | scarcity={result.scarcity_score} | anomalies={len(result.anomalies)}")
        if result.anomalies:
            for a in result.anomalies:
                print(f"  ⚠ [{a.severity}] {a.stress_type} — {a.description}")
        print()
