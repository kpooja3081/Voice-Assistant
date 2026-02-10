"""Side Effects Assessment Agent with severity scoring matrix.

Covers 17 known side effects each with Low/Medium/High severity criteria,
plus an "Others" category for unlisted side effects.
"""

import logging
from .base import AssessmentAgent, AssessmentResult, Severity

logger = logging.getLogger("patient-support-agent")

# Severity scoring matrix — maps each side effect to severity descriptions
# Used for reference; the LLM determines which severity level matches
# based on its conversation with the patient.
SIDE_EFFECT_MATRIX = {
    "oral_pain_ulcers": {
        "high": "Cannot eat at all because of pain/ulcers",
        "medium": "Difficulty in eating",
        "low": "Mild pain in eating",
    },
    "dry_mouth": {
        "high": "Severe dryness and always thirsty",
        "medium": "Moderate dryness and frequently thirsty",
        "low": "Mild dryness",
    },
    "difficulty_breathing": {
        "high": "Too breathless to leave the house",
        "medium": "Stopping for breath after a short walk",
        "low": "Walk slower than people of the same age because of breathlessness",
    },
    "cough": {
        "high": "Distressing cough most of the day",
        "medium": "Frequent cough interfering with daily activities",
        "low": "Frequent cough not interfering with daily activities",
    },
    "nausea": {
        "high": "Cannot consume any solid or liquid food due to nausea",
        "medium": "Can eat or drink very little due to nausea",
        "low": "Can eat but with slight discomfort",
    },
    "vomiting": {
        "high": "Vomited more than 6 times in last 24 hrs",
        "medium": "Vomited 2 to 5 times in last 24 hrs",
        "low": "Vomited once in last 24 hrs",
    },
    "constipation": {
        "high": "Bowel movement once a month and/or always painful",
        "medium": "Bowel movement once a week and/or usually painful",
        "low": "Bowel movement twice a week and/or rarely painful",
    },
    "diarrhea": {
        "high": "7 or more loose/watery stools in a day",
        "medium": "4 to 6 loose/watery stools in a day",
        "low": "Less than 4 loose/watery stools in a day",
    },
    "urinary_problems": {
        "high": "Severe pain while urinating and/or blood in urine",
        "medium": "Moderate burning sensation and frequent urination",
        "low": "Mild burning sensation and frequent urination",
    },
    "tiredness": {
        "high": "Fatigue not relieved by rest, significantly affects daily activities",
        "medium": "Fatigue not relieved by rest, slightly affects daily activities",
        "low": "Fatigue not relieved by rest but can do daily activities",
    },
    "fever": {
        "high": "Fever >40°C for more than 24 hrs",
        "medium": "Fever between 39°C and 40°C",
        "low": "Fever between 38°C and 39°C",
    },
    "loss_of_appetite": {
        "high": "No appetite and lost more than 5% of body weight",
        "medium": "No appetite and lost some weight",
        "low": "Low appetite but no weight loss",
    },
    "skin_rash": {
        "high": "Rash covering more than 2 body parts with burning/itching",
        "medium": "Rash covering large area with/without burning/itching",
        "low": "Rash covering small part with/without burning/itching",
    },
    "skin_itch": {
        "high": "Itching in various parts, constant, affects daily self-care",
        "medium": "Intermittent itching in various parts, affects daily self-care",
        "low": "Mild itching, does not limit daily self-care",
    },
    "swelling_hands_feet": {
        "high": "Ulcers, blisters or severe pain severely affecting daily activities",
        "medium": "Pain, redness affecting daily activities slightly",
        "low": "Mild redness with numbness/tingling or burning sensation",
    },
    "pain": {
        "high": "Pain score 8 to 10",
        "medium": "Pain score 4 to 7",
        "low": "Pain score 2 to 3",
    },
    "others": {
        "high": "Need assistance in daily self-care activities due to the side effect",
        "medium": "Distressing & daily self-care activities become challenging",
        "low": "Problematic but able to do normal daily activities",
    },
}

# Known side effect name aliases → canonical key
SIDE_EFFECT_ALIASES = {
    "oral pain": "oral_pain_ulcers",
    "mouth ulcers": "oral_pain_ulcers",
    "mouth sores": "oral_pain_ulcers",
    "oral ulcers": "oral_pain_ulcers",
    "dry mouth": "dry_mouth",
    "mouth dryness": "dry_mouth",
    "difficulty breathing": "difficulty_breathing",
    "breathlessness": "difficulty_breathing",
    "shortness of breath": "difficulty_breathing",
    "cough": "cough",
    "coughing": "cough",
    "nausea": "nausea",
    "feeling nauseous": "nausea",
    "vomiting": "vomiting",
    "throwing up": "vomiting",
    "constipation": "constipation",
    "diarrhea": "diarrhea",
    "loose stool": "diarrhea",
    "loose stools": "diarrhea",
    "urinary problems": "urinary_problems",
    "urinary pain": "urinary_problems",
    "burning urination": "urinary_problems",
    "tiredness": "tiredness",
    "fatigue": "tiredness",
    "exhaustion": "tiredness",
    "fever": "fever",
    "high temperature": "fever",
    "loss of appetite": "loss_of_appetite",
    "no appetite": "loss_of_appetite",
    "reduced appetite": "loss_of_appetite",
    "skin rash": "skin_rash",
    "rash": "skin_rash",
    "skin itch": "skin_itch",
    "itching": "skin_itch",
    "itchy skin": "skin_itch",
    "swelling": "swelling_hands_feet",
    "swelling of hands": "swelling_hands_feet",
    "swelling of feet": "swelling_hands_feet",
    "hand foot syndrome": "swelling_hands_feet",
    "pain": "pain",
    "body pain": "pain",
}


class SideEffectsAgent(AssessmentAgent):
    """Side effects assessment agent with severity scoring."""

    name = "side_effects_assessment"
    description = "Assesses reported side effects and determines severity"

    def _resolve_side_effect(self, name: str) -> str:
        """Resolve a side effect name to its canonical key."""
        normalized = name.lower().strip()
        return SIDE_EFFECT_ALIASES.get(normalized, "others")

    def assess(
        self,
        side_effect_name: str,
        severity: str,
        details: str = "",
    ) -> AssessmentResult:
        """Assess a single reported side effect.

        Args:
            side_effect_name: Name of the side effect reported
            severity: "low", "medium", or "high"
            details: Additional details from the patient
        """
        canonical = self._resolve_side_effect(side_effect_name)
        sev_lower = severity.lower().strip()

        # Map string to Severity enum
        sev_map = {"low": Severity.LOW, "medium": Severity.MEDIUM, "high": Severity.HIGH}
        sev_enum = sev_map.get(sev_lower, Severity.LOW)

        # Get the severity description from the matrix
        matrix_entry = SIDE_EFFECT_MATRIX.get(canonical, SIDE_EFFECT_MATRIX["others"])
        sev_description = matrix_entry.get(sev_lower, "")

        # High severity side effects should be flagged
        requires_care_team = sev_enum == Severity.HIGH

        summary = (
            f"Side effect '{side_effect_name}' reported with {sev_lower} severity. "
            f"{sev_description}"
        )

        logger.info(
            f"Side effect assessment: {side_effect_name} ({canonical}), "
            f"severity={sev_lower}, care_team={requires_care_team}"
        )

        return AssessmentResult(
            agent_name=self.name,
            score={"low": 1, "medium": 2, "high": 3}.get(sev_lower, 0),
            severity=sev_enum,
            summary=summary,
            details={
                "side_effect_name": side_effect_name,
                "canonical_name": canonical,
                "severity": sev_lower,
                "severity_description": sev_description,
                "patient_details": details,
            },
            requires_care_team=requires_care_team,
        )
