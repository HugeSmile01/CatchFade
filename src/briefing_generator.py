"""
CatchFade - LLM Ecological Briefing Generator
Generates human-readable ecological briefings from detection results.
Supports: Anthropic Claude, OpenAI GPT, Ollama (local), or mock mode.
"""

import os
import json
import logging
from datetime import datetime
from typing import Optional, Literal
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# ─── Briefing Output Model ─────────────────────────────────────────────────────

@dataclass
class EcologicalBriefing:
    timestamp: str
    location_id: str
    briefing_id: str
    llm_provider: str
    ecological_status: str          # One-line status
    detailed_analysis: str          # Full paragraph analysis
    species_risk_assessment: str    # Species at risk
    recommended_actions: str        # What to do next
    confidence_note: str            # LLM confidence caveat
    raw_prompt: str = ""
    raw_response: str = ""

    def to_dict(self):
        return {k: v for k, v in self.__dict__.items() if not k.startswith("_")}

    def to_json(self):
        return json.dumps(self.to_dict(), indent=2)

    def to_report_text(self):
        return f"""
╔══════════════════════════════════════════════════════════════════╗
║          CATCHFADE ECOLOGICAL BRIEFING REPORT                    ║
╚══════════════════════════════════════════════════════════════════╝

Location  : {self.location_id}
Timestamp : {self.timestamp}
Briefing  : {self.briefing_id}
Provider  : {self.llm_provider}

─── ECOLOGICAL STATUS ──────────────────────────────────────────────
{self.ecological_status}

─── DETAILED ANALYSIS ──────────────────────────────────────────────
{self.detailed_analysis}

─── SPECIES RISK ASSESSMENT ────────────────────────────────────────
{self.species_risk_assessment}

─── RECOMMENDED ACTIONS ────────────────────────────────────────────
{self.recommended_actions}

─── CONFIDENCE NOTE ────────────────────────────────────────────────
{self.confidence_note}
══════════════════════════════════════════════════════════════════════
"""


# ─── Prompt Builder ────────────────────────────────────────────────────────────

def build_ecological_prompt(detection_result, sensor_reading) -> str:
    """Build a detailed prompt for LLM ecological analysis."""
    anomaly_block = ""
    if detection_result.anomalies:
        for a in detection_result.anomalies:
            anomaly_block += (
                f"\n  - [{a.severity}] {a.stress_type}: {a.parameter} = {a.observed_value} "
                f"(expected: {a.expected_range})\n    → {a.ecological_implication}"
            )
    else:
        anomaly_block = "\n  No anomalies detected. All parameters within baseline."

    r = sensor_reading.to_dict()

    prompt = f"""You are CatchFade, an autonomous marine ecological monitoring AI system deployed on a coastal habitat.
Your role is to generate a concise, scientifically grounded ecological briefing based on real-time sensor data.

## SENSOR READINGS ({r['timestamp']})
- Water Temperature: {r['temperature_c']} °C
- Salinity: {r['salinity_ppt']} ppt
- Dissolved Oxygen: {r['dissolved_oxygen_mgl']} mg/L
- Turbidity: {r['turbidity_ntu']} NTU
- pH: {r['ph']}
- Water Depth: {r['depth_m']} m
- Acoustic Activity Index: {r['acoustic_activity']} (0=silent, 1=highly active)
- Motion Detected: {r['motion_detected']}
- Ambient Light: {r['light_lux']} lux

## DETECTION RESULTS
- Overall Severity: {detection_result.overall_severity}
- Scarcity Score: {detection_result.scarcity_score}/1.00
- Stress Index: {detection_result.stress_index}/10.00
- Species Activity Low: {detection_result.species_activity_low}
- Habitat Stable: {detection_result.habitat_stable}

## ANOMALIES DETECTED ({len(detection_result.anomalies)} total)
{anomaly_block}

## YOUR TASK
Generate a structured ecological briefing with exactly these four sections:

1. ECOLOGICAL STATUS: One clear sentence summarizing the current condition of this marine habitat.

2. DETAILED ANALYSIS: 2–3 paragraphs interpreting the sensor data in ecological context. Discuss potential causes of observed anomalies. Reference relevant marine biology principles where appropriate (coral reef dynamics, fish behavior, benthic communities, etc.). Focus on the coastal/marine ecosystem.

3. SPECIES RISK ASSESSMENT: Identify which coastal/marine species groups are most at risk based on the observed conditions (e.g., coral, reef fish, invertebrates, marine mammals, seagrass). Explain why each is at risk.

4. RECOMMENDED ACTIONS: Provide 3–5 specific, actionable recommendations for ecological intervention or further investigation.

End with a short CONFIDENCE NOTE explaining the limitations of AI-generated ecological interpretation.

Be scientific but accessible. Avoid speculation beyond what the data supports."""

    return prompt


# ─── LLM Provider Implementations ─────────────────────────────────────────────

class AnthropicProvider:
    """Uses Anthropic Claude API."""

    def __init__(self, api_key: Optional[str] = None, model: str = "claude-sonnet-4-20250514"):
        try:
            import anthropic
            self.client = anthropic.Anthropic(api_key=api_key or os.getenv("ANTHROPIC_API_KEY"))
            self.model = model
            logger.info(f"Anthropic provider ready | model={model}")
        except ImportError:
            raise ImportError("Run: pip install anthropic")

    def complete(self, prompt: str) -> str:
        message = self.client.messages.create(
            model=self.model,
            max_tokens=1200,
            messages=[{"role": "user", "content": prompt}]
        )
        return message.content[0].text


class OpenAIProvider:
    """Uses OpenAI GPT API."""

    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o"):
        try:
            from openai import OpenAI
            self.client = OpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))
            self.model = model
            logger.info(f"OpenAI provider ready | model={model}")
        except ImportError:
            raise ImportError("Run: pip install openai")

    def complete(self, prompt: str) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1200,
        )
        return response.choices[0].message.content


class OllamaProvider:
    """Uses local Ollama instance (no internet required after setup)."""

    def __init__(self, model: str = "llama3", base_url: str = "http://localhost:11434"):
        try:
            import requests
            self.requests = requests
            self.model = model
            self.base_url = base_url
            logger.info(f"Ollama provider ready | model={model} | url={base_url}")
        except ImportError:
            raise ImportError("Run: pip install requests")

    def complete(self, prompt: str) -> str:
        response = self.requests.post(
            f"{self.base_url}/api/generate",
            json={"model": self.model, "prompt": prompt, "stream": False},
            timeout=120
        )
        response.raise_for_status()
        return response.json()["response"]


class MockProvider:
    """Returns a static mock briefing for development/testing without any API."""

    def complete(self, prompt: str) -> str:
        return """1. ECOLOGICAL STATUS: This coastal marine habitat is exhibiting signs of moderate ecological stress with elevated thermal conditions and reduced biological acoustic activity suggesting possible species displacement.

2. DETAILED ANALYSIS: The recorded water temperature of 34.2°C exceeds the thermal tolerance threshold for most reef-building corals (typically 28–30°C), indicating a high risk of coral bleaching event. Simultaneously, dissolved oxygen levels at 2.5 mg/L have entered hypoxic territory, which is acutely stressful for demersal fish species and benthic invertebrates. These parameters in combination suggest a compounding stress event, potentially driven by localized upwelling disruption or surface thermal stratification reducing oxygen mixing.

The low acoustic activity index (0.04) is particularly significant. Marine environments maintain characteristic bioacoustic profiles through reef fish choruses, snapping shrimp, and cetacean vocalizations. A near-silent hydrophone reading concurrent with physical stressors strongly indicates active species avoidance or displacement rather than natural diurnal quiet.

3. SPECIES RISK ASSESSMENT: Coral (Acropora spp., Porites spp.) — HIGH RISK due to thermal bleaching threshold exceedance. Reef fish assemblages (labridae, serranidae) — HIGH RISK from hypoxia and habitat flight. Benthic invertebrates (sea urchins, mollusks) — CRITICAL RISK from pH drop and hypoxia. Seagrass beds — MODERATE RISK from turbidity limiting photosynthesis.

4. RECOMMENDED ACTIONS:
- Deploy additional temperature loggers at 1m depth intervals to characterize thermal stratification profile.
- Conduct urgent visual transect survey within 24 hours to assess coral bleaching extent.
- Increase sampling frequency to 15-minute intervals until DO recovers above 5 mg/L.
- Alert local marine protected area (MPA) managers for potential emergency response activation.
- Cross-reference with satellite SST data to determine if thermal anomaly is localized or regional.

CONFIDENCE NOTE: This briefing is generated by an AI system from autonomous sensor data and should be validated by a qualified marine biologist before any management decisions are made. Sensor drift, biofouling, or local physical disturbances may produce false readings."""


# ─── Briefing Generator ────────────────────────────────────────────────────────

class EcologicalBriefingGenerator:
    """
    Main class that ties sensor reading + detection result into an LLM briefing.
    Auto-selects provider based on config or falls back gracefully.
    """

    PROVIDERS = {
        "anthropic": AnthropicProvider,
        "openai": OpenAIProvider,
        "ollama": OllamaProvider,
        "mock": MockProvider,
    }

    def __init__(
        self,
        provider: Literal["anthropic", "openai", "ollama", "mock"] = "mock",
        **provider_kwargs
    ):
        self.provider_name = provider
        try:
            if provider == "mock":
                self.llm = MockProvider()
            else:
                self.llm = self.PROVIDERS[provider](**provider_kwargs)
        except Exception as e:
            logger.warning(f"Provider '{provider}' failed ({e}). Falling back to mock.")
            self.llm = MockProvider()
            self.provider_name = "mock (fallback)"

    def generate(self, detection_result, sensor_reading) -> EcologicalBriefing:
        """Generate a full ecological briefing."""
        prompt = build_ecological_prompt(detection_result, sensor_reading)
        logger.info(f"Generating briefing via {self.provider_name}...")

        raw_response = self.llm.complete(prompt)

        # Parse structured sections
        def extract_section(text: str, label: str, next_label: Optional[str] = None) -> str:
            try:
                start = text.find(label)
                if start == -1:
                    return "Not available."
                start = text.find(":", start) + 1
                if next_label:
                    end = text.find(next_label, start)
                    return text[start:end].strip() if end != -1 else text[start:].strip()
                return text[start:].strip()
            except Exception:
                return text.strip()

        ecological_status = extract_section(raw_response, "1. ECOLOGICAL STATUS", "2. DETAILED")
        detailed_analysis = extract_section(raw_response, "2. DETAILED ANALYSIS", "3. SPECIES")
        species_risk = extract_section(raw_response, "3. SPECIES RISK ASSESSMENT", "4. RECOMMENDED")
        recommended = extract_section(raw_response, "4. RECOMMENDED ACTIONS", "CONFIDENCE NOTE")
        confidence = extract_section(raw_response, "CONFIDENCE NOTE")

        briefing_id = f"CF-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"

        briefing = EcologicalBriefing(
            timestamp=sensor_reading.timestamp,
            location_id=sensor_reading.location_id,
            briefing_id=briefing_id,
            llm_provider=self.provider_name,
            ecological_status=ecological_status or "Status not parsed.",
            detailed_analysis=detailed_analysis or raw_response,
            species_risk_assessment=species_risk or "Not available.",
            recommended_actions=recommended or "Not available.",
            confidence_note=confidence or "AI-generated. Validate with expert review.",
            raw_prompt=prompt,
            raw_response=raw_response,
        )

        logger.info(f"Briefing generated: {briefing_id}")
        return briefing


# ─── Entry Point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    sys.path.insert(0, ".")
    from sensor_manager import SensorManager
    from anomaly_detector import AnomalyDetector

    manager = SensorManager(simulated=True)
    detector = AnomalyDetector()

    # Use mock by default; change to "anthropic", "openai", or "ollama" with API keys
    generator = EcologicalBriefingGenerator(provider="mock")

    reading = manager.collect()
    result = detector.detect(reading)
    briefing = generator.generate(result, reading)

    print(briefing.to_report_text())
