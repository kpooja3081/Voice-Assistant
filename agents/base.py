"""Base classes and data models for assessment agents."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class Severity(Enum):
    """Severity levels for assessments."""
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class AssessmentResult:
    """Structured result from an assessment agent."""
    agent_name: str
    score: Optional[float] = None
    severity: Severity = Severity.NONE
    summary: str = ""
    details: dict = field(default_factory=dict)
    requires_care_team: bool = False
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return {
            "agent_name": self.agent_name,
            "score": self.score,
            "severity": self.severity.value,
            "summary": self.summary,
            "details": self.details,
            "requires_care_team": self.requires_care_team,
            "timestamp": self.timestamp,
        }


class AssessmentAgent:
    """Base class for all assessment agents."""

    name: str = "base"
    description: str = "Base assessment agent"

    def assess(self, **kwargs) -> AssessmentResult:
        raise NotImplementedError("Subclasses must implement assess()")
