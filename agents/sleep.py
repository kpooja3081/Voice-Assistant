"""Sleep Assessment Agent.

Guidelines:
- A person should take 7 to 9 hours of good quality sleep.
- Duration and quality are both important.
- If sleep is poor, ask: falling asleep vs. staying asleep problem.
- Ask if patient needs doctor help for sleep issues.
- No further medical recommendations needed.
"""

import logging
from .base import AssessmentAgent, AssessmentResult, Severity

logger = logging.getLogger("patient-support-agent")


class SleepAgent(AssessmentAgent):
    """Sleep quality and duration assessment agent."""

    name = "sleep_assessment"
    description = "Assesses sleep duration, quality, and related problems"

    def assess(
        self,
        duration_hours: float,
        quality: str,
        problem_type: str = "none",
        needs_doctor_help: bool = False,
    ) -> AssessmentResult:
        """Run sleep assessment.

        Args:
            duration_hours: Approximate hours of sleep per night
            quality: "good" or "poor"
            problem_type: "falling_asleep", "staying_asleep", "both", or "none"
            needs_doctor_help: Whether patient wants doctor help for sleep
        """
        duration = float(duration_hours)
        quality_lower = quality.lower().strip()
        problem = problem_type.lower().strip()

        issues = []
        if duration < 7:
            issues.append(f"Below recommended duration ({duration:.1f}h vs 7-9h)")
        elif duration > 9:
            issues.append(f"Above recommended duration ({duration:.1f}h vs 7-9h)")

        if quality_lower == "poor":
            issues.append("Poor sleep quality reported")

        if problem not in ("none", ""):
            problem_desc = {
                "falling_asleep": "Difficulty falling asleep",
                "staying_asleep": "Difficulty staying asleep",
                "both": "Difficulty falling and staying asleep",
            }
            issues.append(problem_desc.get(problem, f"Sleep problem: {problem}"))

        # Determine severity
        if not issues:
            severity = Severity.NONE
            summary = "Sleep is within normal range — good duration and quality."
        elif len(issues) == 1 and quality_lower == "good":
            severity = Severity.LOW
            summary = "Minor sleep concern noted."
        elif quality_lower == "poor" and duration < 7:
            severity = Severity.HIGH
            summary = "Poor sleep quality with insufficient duration."
        else:
            severity = Severity.MEDIUM
            summary = "Sleep concerns noted that may benefit from attention."

        logger.info(
            f"Sleep assessment: {duration}h, quality={quality_lower}, "
            f"problem={problem}, severity={severity.value}"
        )

        return AssessmentResult(
            agent_name=self.name,
            score=duration,
            severity=severity,
            summary=summary,
            details={
                "duration_hours": duration,
                "quality": quality_lower,
                "problem_type": problem,
                "needs_doctor_help": needs_doctor_help,
                "issues": issues,
            },
            requires_care_team=needs_doctor_help,
        )
