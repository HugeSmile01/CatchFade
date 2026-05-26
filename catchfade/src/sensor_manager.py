"""
CatchFade - Sensor Manager
Handles all aquatic sensor data collection for coastal/marine monitoring.
Supports real hardware (Raspberry Pi GPIO) and simulated mode for testing.
"""

import time
import random
import json
import logging
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import Optional

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# ─── Data Models ──────────────────────────────────────────────────────────────

@dataclass
class SensorReading:
    timestamp: str
    temperature_c: float          # Water temperature (°C)
    salinity_ppt: float           # Salinity (parts per thousand)
    dissolved_oxygen_mgl: float   # DO (mg/L) — critical for marine life
    turbidity_ntu: float          # Turbidity (NTU) — water clarity
    ph: float                     # pH level
    depth_m: float                # Water depth (m)
    acoustic_activity: float      # Hydrophone activity index (0–1)
    motion_detected: bool         # Underwater motion sensor
    light_lux: float              # Ambient light (for time-of-day context)
    location_id: str              # Sensor node ID

    def to_dict(self):
        return asdict(self)

    def to_json(self):
        return json.dumps(self.to_dict(), indent=2)


# ─── Baseline Thresholds (Coastal/Marine) ─────────────────────────────────────

MARINE_BASELINES = {
    "temperature_c":          {"min": 20.0, "max": 30.0, "critical_low": 15.0, "critical_high": 35.0},
    "salinity_ppt":           {"min": 30.0, "max": 38.0, "critical_low": 25.0, "critical_high": 45.0},
    "dissolved_oxygen_mgl":   {"min": 5.0,  "max": 9.0,  "critical_low": 3.0,  "critical_high": 12.0},
    "turbidity_ntu":          {"min": 0.0,  "max": 10.0, "critical_low": 0.0,  "critical_high": 50.0},
    "ph":                     {"min": 7.8,  "max": 8.3,  "critical_low": 7.4,  "critical_high": 8.7},
    "acoustic_activity":      {"min": 0.2,  "max": 0.8,  "critical_low": 0.05, "critical_high": 1.0},
}


# ─── Hardware Sensor Interface ─────────────────────────────────────────────────

class HardwareSensorInterface:
    """
    Interface for real hardware sensors connected via Raspberry Pi GPIO / I2C / UART.
    Replace each method body with your actual sensor library calls.
    
    Recommended sensors:
    - Temperature/Salinity: Atlas Scientific EZO-EC + EZO-RTD
    - Dissolved Oxygen: Atlas Scientific EZO-DO
    - Turbidity: DF Robot SEN0189 or Gravity Turbidity
    - pH: Atlas Scientific EZO-pH
    - Depth: Blue Robotics Bar30
    - Acoustic: Aquarian Audio H2a hydrophone + ADC (ADS1115)
    - Motion: PIR or sonar module (HC-SR04 waterproofed)
    - Light: TSL2591 or BH1750
    """

    def __init__(self):
        try:
            import board
            import busio
            self.i2c = busio.I2C(board.SCL, board.SDA)
            self.hardware_available = True
            logger.info("Hardware I2C interface initialized.")
        except Exception as e:
            self.hardware_available = False
            logger.warning(f"Hardware not available ({e}). Use SimulatedSensorInterface.")

    def read_temperature(self) -> float:
        # Replace with: return self.ezo_rtd.read()
        raise NotImplementedError("Connect Atlas EZO-RTD sensor")

    def read_salinity(self) -> float:
        # Replace with: return self.ezo_ec.read()
        raise NotImplementedError("Connect Atlas EZO-EC sensor")

    def read_dissolved_oxygen(self) -> float:
        # Replace with: return self.ezo_do.read()
        raise NotImplementedError("Connect Atlas EZO-DO sensor")

    def read_turbidity(self) -> float:
        # Replace with: return self.turbidity_sensor.read()
        raise NotImplementedError("Connect turbidity sensor")

    def read_ph(self) -> float:
        # Replace with: return self.ezo_ph.read()
        raise NotImplementedError("Connect Atlas EZO-pH sensor")

    def read_depth(self) -> float:
        # Replace with: return self.bar30.depth()
        raise NotImplementedError("Connect Blue Robotics Bar30")

    def read_acoustic_activity(self) -> float:
        # Replace with: return self.hydrophone.read_rms()
        raise NotImplementedError("Connect hydrophone + ADC")

    def read_motion(self) -> bool:
        # Replace with: return GPIO.input(PIR_PIN)
        raise NotImplementedError("Connect motion sensor")

    def read_light(self) -> float:
        # Replace with: return self.tsl.lux
        raise NotImplementedError("Connect TSL2591 sensor")


# ─── Simulated Sensor Interface ────────────────────────────────────────────────

class SimulatedSensorInterface:
    """
    Simulates realistic coastal/marine sensor data for testing and development.
    Includes drift, noise, and occasional anomaly injection.
    """

    def __init__(self, anomaly_rate: float = 0.05):
        self.anomaly_rate = anomaly_rate
        self._time_offset = 0
        logger.info("Simulated sensor interface initialized.")

    def _noisy(self, base: float, noise: float = 0.02) -> float:
        """Add Gaussian noise to a base value."""
        return round(base + random.gauss(0, base * noise), 3)

    def _maybe_anomaly(self, normal_val: float, anomaly_val: float) -> float:
        if random.random() < self.anomaly_rate:
            return anomaly_val
        return normal_val

    def read_temperature(self) -> float:
        return self._noisy(self._maybe_anomaly(26.5, 34.2))

    def read_salinity(self) -> float:
        return self._noisy(self._maybe_anomaly(34.5, 23.0))

    def read_dissolved_oxygen(self) -> float:
        return self._noisy(self._maybe_anomaly(6.8, 2.5))

    def read_turbidity(self) -> float:
        return self._noisy(self._maybe_anomaly(4.2, 55.0))

    def read_ph(self) -> float:
        return self._noisy(self._maybe_anomaly(8.1, 7.2))

    def read_depth(self) -> float:
        return self._noisy(3.5, noise=0.01)

    def read_acoustic_activity(self) -> float:
        return round(self._maybe_anomaly(random.uniform(0.3, 0.7), 0.04), 3)

    def read_motion(self) -> bool:
        return random.random() > 0.6

    def read_light(self) -> float:
        hour = datetime.now().hour
        if 6 <= hour <= 18:
            return self._noisy(random.uniform(1000, 8000), noise=0.1)
        return self._noisy(random.uniform(0, 50), noise=0.5)


# ─── Sensor Manager ────────────────────────────────────────────────────────────

class SensorManager:
    """
    Main orchestrator that reads all sensors, validates readings, and returns
    a structured SensorReading dataclass.
    """

    def __init__(self, location_id: str = "CF-NODE-01", simulated: bool = True):
        self.location_id = location_id
        self.interface = SimulatedSensorInterface() if simulated else HardwareSensorInterface()
        logger.info(f"SensorManager ready | node={location_id} | mode={'simulated' if simulated else 'hardware'}")

    def collect(self) -> SensorReading:
        """Collect one full reading from all sensors."""
        reading = SensorReading(
            timestamp=datetime.utcnow().isoformat() + "Z",
            temperature_c=self.interface.read_temperature(),
            salinity_ppt=self.interface.read_salinity(),
            dissolved_oxygen_mgl=self.interface.read_dissolved_oxygen(),
            turbidity_ntu=self.interface.read_turbidity(),
            ph=self.interface.read_ph(),
            depth_m=self.interface.read_depth(),
            acoustic_activity=self.interface.read_acoustic_activity(),
            motion_detected=self.interface.read_motion(),
            light_lux=self.interface.read_light(),
            location_id=self.location_id,
        )
        logger.debug(f"Reading collected: {reading.to_json()}")
        return reading

    def collect_batch(self, count: int = 10, interval_sec: float = 1.0) -> list:
        """Collect multiple readings with a delay between each."""
        readings = []
        for i in range(count):
            readings.append(self.collect())
            if i < count - 1:
                time.sleep(interval_sec)
        return readings


# ─── Entry Point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    manager = SensorManager(location_id="CF-NODE-COASTAL-01", simulated=True)
    print("\n=== CatchFade Single Reading ===")
    reading = manager.collect()
    print(reading.to_json())

    print("\n=== CatchFade Batch (3 readings) ===")
    batch = manager.collect_batch(count=3, interval_sec=0.5)
    for r in batch:
        print(f"[{r.timestamp}] DO={r.dissolved_oxygen_mgl} mg/L | Salinity={r.salinity_ppt} ppt | Acoustic={r.acoustic_activity}")
