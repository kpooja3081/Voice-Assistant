"""Patient data tools for reading history and storing conversation outcomes.

Design: Zero latency during calls.
- load_patient_context() is called BEFORE the call starts
- save_call_notes() is called AFTER the call ends
"""

import json
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger("patient-support-agent")

DATA_DIR = Path(__file__).parent.parent / "data" / "patients"


def _find_patient_file(patient_id: str) -> Path | None:
    """Find the JSON file for a patient by ID."""
    # Try exact filename
    path = DATA_DIR / f"{patient_id}.json"
    if path.exists():
        return path

    # Search by patient_id field
    for f in DATA_DIR.glob("*.json"):
        data = json.loads(f.read_text(encoding="utf-8"))
        if data.get("patient_id", "").lower() == patient_id.lower():
            return f

    return None


def load_patient_context(patient_id: str) -> str | None:
    """Load patient info to inject into the system prompt before the call.

    Returns a context string or None if patient not found.
    """
    path = _find_patient_file(patient_id)
    if not path:
        logger.warning(f"No patient found: {patient_id}")
        return None

    data = json.loads(path.read_text(encoding="utf-8"))

    meds = "\n".join(
        f"  - {m['name']} {m['dose']} ({m['frequency']})"
        for m in data.get("medications", [])
    )
    conditions = ", ".join(data.get("conditions", []))
    allergies = ", ".join(data.get("allergies", []))
    last_call = data.get("last_call") or "No previous calls"

    # Build previous call summaries if any
    history = ""
    for call in data.get("call_history", [])[-3:]:  # last 3 calls
        history += f"\n  - {call['date'][:10]}: {call.get('summary', 'No summary')}"

    return (
        f"\n## PATIENT INFORMATION (pre-loaded, do not ask for this)\n"
        f"Name: {data['name']}\n"
        f"Patient ID: {data['patient_id']}\n"
        f"Age: {data.get('age', 'Unknown')}\n"
        f"Conditions: {conditions or 'None listed'}\n"
        f"Medications:\n{meds or '  None listed'}\n"
        f"Allergies: {allergies or 'None known'}\n"
        f"Provider: {data.get('provider', 'Unknown')}\n"
        f"Last call: {last_call}"
        f"{f'{chr(10)}Recent call history:{history}' if history else ''}"
    )


def save_call_notes(patient_id: str, chat_history: list[dict]) -> None:
    """Save conversation notes after the call ends. Runs async-safe, no latency impact.

    Extracts a simple record from the raw chat history and appends to patient file.
    """
    path = _find_patient_file(patient_id)
    if not path:
        logger.error(f"Cannot save notes: patient {patient_id} not found")
        return

    data = json.loads(path.read_text(encoding="utf-8"))

    # Extract conversation text
    transcript = []
    for msg in chat_history:
        role = msg.get("role", "unknown")
        text = msg.get("text", msg.get("content", ""))
        if text:
            transcript.append(f"{role}: {text}")

    call_record = {
        "date": datetime.now().isoformat(),
        "transcript": transcript,
    }

    data.setdefault("call_history", []).append(call_record)
    data["last_call"] = call_record["date"]

    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    logger.info(f"Call notes saved for patient {patient_id}")
