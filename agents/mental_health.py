"""Mental Health Assessment Agent — PHQ-2 screening.

Questions:
  Q1: Over the past 2 weeks, have you experienced little interest or pleasure
      in doing things you usually enjoy?
  Q2: Have you been feeling down, depressed, or hopeless?

Scoring per question (0-3):
  0 – Not at all
  1 – Several days
  2 – More than half the days
  3 – Nearly every day

If total score >= 3 → flag for care team.
"""

import logging
from .base import AssessmentAgent, AssessmentResult, Severity

logger = logging.getLogger("patient-support-agent")

SCORE_LABELS = {
    0: "Not at all",
    1: "Several days",
    2: "More than half the days",
    3: "Nearly every day",
}


class MentalHealthAgent(AssessmentAgent):
    """PHQ-2 based mental health screening agent."""

    name = "mental_health_assessment"
    description = "Screens for depression risk using PHQ-2 questionnaire"

    def assess(self, q1_score: int, q2_score: int) -> AssessmentResult:
        """Run PHQ-2 assessment.

        Args:
            q1_score: Score for interest/pleasure question (0-3)
            q2_score: Score for feeling down/depressed question (0-3)
        """
        # Clamp scores to valid range
        q1 = max(0, min(3, int(q1_score)))
        q2 = max(0, min(3, int(q2_score)))
        total = q1 + q2

        requires_care_team = total >= 3

        if total == 0:
            severity = Severity.NONE
            summary = "No signs of depression risk detected."
        elif total <= 2:
            severity = Severity.LOW
            summary = "Mild indicators noted. No immediate concern."
        elif total <= 4:
            severity = Severity.MEDIUM
            summary = "Moderate depression risk indicators. Care team will be informed."
        else:
            severity = Severity.HIGH
            summary = "Significant depression risk indicators. Care team will be informed."

        logger.info(
            f"Mental health assessment: Q1={q1}, Q2={q2}, total={total}, "
            f"severity={severity.value}, care_team={requires_care_team}"
        )

        return AssessmentResult(
            agent_name=self.name,
            score=total,
            severity=severity,
            summary=summary,
            details={
                "q1_interest_pleasure": {"score": q1, "label": SCORE_LABELS[q1]},
                "q2_feeling_down": {"score": q2, "label": SCORE_LABELS[q2]},
                "total_score": total,
                "threshold": 3,
            },
            requires_care_team=requires_care_team,
        )
