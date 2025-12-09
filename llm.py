import logging
import re
from typing import Any, Dict, List, Optional

try:
    import ollama  # type: ignore
except Exception:  # pragma: no cover
    ollama = None  # type: ignore

MODEL_NAME = "llama3.2:3b"


def _ollama_generate(prompt: str) -> Optional[str]:
    if not ollama:
        logging.warning("Ollama not available; returning None")
        return None
    try:
        resp = ollama.generate(model=MODEL_NAME, prompt=prompt)
        text = (resp or {}).get("response")
        return text
    except Exception as e:
        logging.exception("Ollama generation failed: %s", e)
        return None


def score_lead_llm(budget_range: str, vehicle: str, source: str) -> int:
    prompt = (
        f"Score this automotive lead from 0-100 based on budget {budget_range}, interest in {vehicle}, "
        f"source {source}. Return only the numeric score."
    )
    text = _ollama_generate(prompt)
    if text:
        match = re.search(r"(\d{1,3})", text)
        if match:
            score = int(match.group(1))
            return max(0, min(100, score))
    # Heuristic fallback
    score = 50
    if any(k in budget_range.lower() for k in ["10", "12", "15", "crore"]):
        score += 20
    if source in {"referral", "website_form"}:
        score += 10
    if any(m in vehicle.lower() for m in ["rolls", "bentley", "ghost", "phantom", "flying spur"]):
        score += 10
    return max(0, min(100, score))


def generate_welcome_email(name: str, vehicle: str) -> str:
    prompt = (
        f"Write a personalized luxury car dealership welcome email for {name} interested in {vehicle}. "
        f"Tone: professional, premium, non-pushy. Max 150 words."
    )
    text = _ollama_generate(prompt)
    if text:
        return text.strip()
    return (
        f"Dear {name},\n\n"
        f"Thank you for your interest in the exquisite {vehicle}. Our specialist team would be delighted to assist you "
        f"with a private consultation tailored to your preferences. We can arrange a curated viewing and discuss bespoke options "
        f"at your convenience.\n\nWarm regards,\nLuxury Sales Team"
    )


def suggest_followup_actions(classification: str) -> List[str]:
    prompt = (
        f"Suggest 3 next actions for a {classification} automotive lead. Format: action_name_in_snake_case"
    )
    text = _ollama_generate(prompt)
    if text:
        actions = [a.strip().lower().replace(" ", "_") for a in re.split(r"[\n,]", text) if a.strip()]
        return actions[:3]
    if classification == "hot_lead":
        return ["qualification_call_in_4h", "quotation_generation_after_call", "followup_email_in_1_day"]
    if classification == "warm_prospect":
        return ["qualification_call_in_24h", "brochure_email_in_2_days", "followup_email_in_3_days"]
    return ["nurture_email_sequence_weekly"]

