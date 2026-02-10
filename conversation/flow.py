"""Conversation flow management for the Patient Support Voice Agent."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
from datetime import datetime


class ConversationStage(Enum):
    """Stages of the patient support conversation."""
    GREETING = "greeting"
    IDENTITY_VERIFICATION = "identity_verification"
    MEDICATION_ADHERENCE = "medication_adherence"
    SIDE_EFFECTS_INQUIRY = "side_effects_inquiry"
    SIDE_EFFECTS_DETAILS = "side_effects_details"
    ADDITIONAL_CONCERNS = "additional_concerns"
    CLOSING = "closing"
    ENDED = "ended"


class SideEffectSeverity(Enum):
    """Severity levels for reported side effects."""
    MILD = "mild"
    MODERATE = "moderate"
    SEVERE = "severe"
    UNKNOWN = "unknown"


@dataclass
class SideEffect:
    """A reported side effect."""
    description: str
    severity: SideEffectSeverity = SideEffectSeverity.UNKNOWN
    frequency: Optional[str] = None
    duration: Optional[str] = None


@dataclass
class PatientResponse:
    """Collected patient responses during the call."""
    call_id: str
    timestamp: datetime = field(default_factory=datetime.now)
    patient_verified: bool = False
    taking_medication: Optional[bool] = None
    adherence_issues: Optional[str] = None
    side_effects: list[SideEffect] = field(default_factory=list)
    additional_concerns: Optional[str] = None
    wants_callback: bool = False
    call_completed: bool = False
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary for logging/storage."""
        return {
            "call_id": self.call_id,
            "timestamp": self.timestamp.isoformat(),
            "patient_verified": self.patient_verified,
            "taking_medication": self.taking_medication,
            "adherence_issues": self.adherence_issues,
            "side_effects": [
                {
                    "description": se.description,
                    "severity": se.severity.value,
                    "frequency": se.frequency,
                    "duration": se.duration,
                }
                for se in self.side_effects
            ],
            "additional_concerns": self.additional_concerns,
            "wants_callback": self.wants_callback,
            "call_completed": self.call_completed,
            "notes": self.notes,
        }


class ConversationState:
    """Manages the state and flow of a patient support conversation."""

    def __init__(self, call_id: str, patient_name: Optional[str] = None):
        self.call_id = call_id
        self.patient_name = patient_name
        self.stage = ConversationStage.GREETING
        self.response = PatientResponse(call_id=call_id)
        self.message_history: list[dict] = []

    def advance_stage(self) -> ConversationStage:
        """Move to the next conversation stage."""
        stage_order = [
            ConversationStage.GREETING,
            ConversationStage.IDENTITY_VERIFICATION,
            ConversationStage.MEDICATION_ADHERENCE,
            ConversationStage.SIDE_EFFECTS_INQUIRY,
            ConversationStage.SIDE_EFFECTS_DETAILS,
            ConversationStage.ADDITIONAL_CONCERNS,
            ConversationStage.CLOSING,
            ConversationStage.ENDED,
        ]

        current_idx = stage_order.index(self.stage)
        if current_idx < len(stage_order) - 1:
            self.stage = stage_order[current_idx + 1]

        return self.stage

    def set_stage(self, stage: ConversationStage) -> None:
        """Set the conversation stage directly."""
        self.stage = stage

    def add_message(self, role: str, content: str) -> None:
        """Add a message to the conversation history."""
        self.message_history.append({"role": role, "content": content})

    def record_adherence(self, taking: bool, issues: Optional[str] = None) -> None:
        """Record medication adherence information."""
        self.response.taking_medication = taking
        self.response.adherence_issues = issues

    def add_side_effect(
        self,
        description: str,
        severity: SideEffectSeverity = SideEffectSeverity.UNKNOWN,
        frequency: Optional[str] = None,
        duration: Optional[str] = None,
    ) -> None:
        """Add a reported side effect."""
        self.response.side_effects.append(
            SideEffect(
                description=description,
                severity=severity,
                frequency=frequency,
                duration=duration,
            )
        )

    def add_note(self, note: str) -> None:
        """Add a general note to the response."""
        self.response.notes.append(note)

    def complete_call(self) -> PatientResponse:
        """Mark the call as completed and return the response."""
        self.response.call_completed = True
        self.stage = ConversationStage.ENDED
        return self.response

    def get_stage_prompt(self) -> str:
        """Get a prompt hint for the current conversation stage."""
        prompts = {
            ConversationStage.GREETING: "Start with a warm greeting and ask if it's a good time to talk.",
            ConversationStage.IDENTITY_VERIFICATION: "Verify you're speaking with the right person.",
            ConversationStage.MEDICATION_ADHERENCE: "Ask if they've been taking their medication as prescribed.",
            ConversationStage.SIDE_EFFECTS_INQUIRY: "Ask if they've experienced any side effects.",
            ConversationStage.SIDE_EFFECTS_DETAILS: "Get more details about the side effects (severity, frequency).",
            ConversationStage.ADDITIONAL_CONCERNS: "Ask if there's anything else they'd like to share with their care team.",
            ConversationStage.CLOSING: "Thank them for their time and let them know their feedback will be shared with their care team.",
            ConversationStage.ENDED: "The call has ended.",
        }
        return prompts.get(self.stage, "")
