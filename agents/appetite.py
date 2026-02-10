"""Appetite Assessment Agent.

Guidelines:
- Ask: "In the last week, has your appetite been normal?"
- Elaboration: "Do you feel hungry as usual? Or is your hunger reduced or improved?"
- If appetite is reduced → ask about weight loss.
- If sudden weight loss > 5% of body weight → report to care team.
- Note: Appetite = hunger. Low appetite ≠ inability to eat from other symptoms.
"""

import logging
from .base import AssessmentAgent, AssessmentResult, Severity

logger = logging.getLogger("patient-support-agent")


class AppetiteAgent(AssessmentAgent):
    """Appetite and weight loss assessment agent."""

    name = "appetite_assessment"
    description = "Assesses appetite changes and related weight loss"

    def assess(
        self,
        appetite_normal: bool,
        weight_loss_percent: float = 0.0,
    ) -> AssessmentResult:
        """Run appetite assessment.

        Args:
            appetite_normal: Whether patient reports normal appetite
            weight_loss_percent: Percentage of body weight lost (0 if none)
        """
        wl = max(0.0, float(weight_loss_percent))

        if appetite_normal:
            severity = Severity.NONE
            summary = "Appetite is normal. No concerns."
            requires_care_team = False
        elif wl > 5.0:
            severity = Severity.HIGH
            summary = (
                f"Reduced appetite with significant weight loss ({wl:.1f}% of body weight). "
                "This will be reported to the care team."
            )
            requires_care_team = True
        elif wl > 0:
            severity = Severity.MEDIUM
            summary = f"Reduced appetite with some weight loss ({wl:.1f}%)."
            requires_care_team = False
        else:
            severity = Severity.LOW
            summary = "Reduced appetite reported but no weight loss."
            requires_care_team = False

        logger.info(
            f"Appetite assessment: normal={appetite_normal}, "
            f"weight_loss={wl}%, severity={severity.value}, "
            f"care_team={requires_care_team}"
        )

        return AssessmentResult(
            agent_name=self.name,
            score=wl,
            severity=severity,
            summary=summary,
            details={
                "appetite_normal": appetite_normal,
                "weight_loss_percent": wl,
                "threshold_for_care_team": 5.0,
            },
            requires_care_team=requires_care_team,
        )
