"""Orchestrator — registers assessment agents as callable tool functions.

These functions are registered with the LiveKit AgentSession so the main LLM
can invoke them via function calling. Each function runs the assessment logic
and stores the result in a shared list.
"""

import json
import logging
from typing import Annotated

from livekit.agents import llm

from .base import AssessmentResult
from .mental_health import MentalHealthAgent
from .sleep import SleepAgent
from .appetite import AppetiteAgent
from .side_effects import SideEffectsAgent

logger = logging.getLogger("patient-support-agent")


class AssessmentContext:
    """Shared context that accumulates assessment results during a call."""

    def __init__(self):
        self.results: list[AssessmentResult] = []
        self._mental_health = MentalHealthAgent()
        self._sleep = SleepAgent()
        self._appetite = AppetiteAgent()
        self._side_effects = SideEffectsAgent()

    def get_results_summary(self) -> list[dict]:
        """Get all results as serializable dicts."""
        return [r.to_dict() for r in self.results]


class AssessmentFunctions(llm.FunctionContext):
    """LLM-callable tool functions for patient assessments.

    These are registered with the AgentSession so the Gemini LLM can invoke
    them during the conversation when it has gathered enough information.
    """

    def __init__(self):
        super().__init__()
        self._ctx = AssessmentContext()

    @property
    def context(self) -> AssessmentContext:
        return self._ctx

    @llm.ai_callable(
        description=(
            "Assess the patient's mental health using PHQ-2 screening. "
            "Call this AFTER asking both PHQ-2 questions: "
            "Q1 (interest/pleasure in activities) and Q2 (feeling down/depressed). "
            "Score each answer: 0=Not at all, 1=Several days, "
            "2=More than half the days, 3=Nearly every day."
        )
    )
    async def assess_mental_health(
        self,
        q1_score: Annotated[int, llm.TypeInfo(
            description="Score for Q1 'little interest or pleasure in doing things' (0-3)"
        )],
        q2_score: Annotated[int, llm.TypeInfo(
            description="Score for Q2 'feeling down, depressed, or hopeless' (0-3)"
        )],
    ) -> str:
        """Run mental health PHQ-2 assessment and store result."""
        result = self._ctx._mental_health.assess(q1_score=q1_score, q2_score=q2_score)
        self._ctx.results.append(result)

        response = f"Mental Health Assessment Complete — Total Score: {result.score}/6. "
        if result.requires_care_team:
            response += "Score is 3 or above. Please inform the patient that you will share this with the care team for further help."
        else:
            response += "Score is below 3. No immediate concern."
        return response

    @llm.ai_callable(
        description=(
            "Assess the patient's sleep quality and duration. "
            "Call this AFTER asking about sleep duration, quality, "
            "and any problems (falling asleep / staying asleep). "
            "Normal sleep is 7-9 hours of good quality."
        )
    )
    async def assess_sleep(
        self,
        duration_hours: Annotated[float, llm.TypeInfo(
            description="Approximate hours of sleep per night"
        )],
        quality: Annotated[str, llm.TypeInfo(
            description="Sleep quality: 'good' or 'poor'"
        )],
        problem_type: Annotated[str, llm.TypeInfo(
            description="Type of sleep problem: 'falling_asleep', 'staying_asleep', 'both', or 'none'"
        )] = "none",
        needs_doctor_help: Annotated[bool, llm.TypeInfo(
            description="Whether the patient wants doctor help for sleep issues"
        )] = False,
    ) -> str:
        """Run sleep assessment and store result."""
        result = self._ctx._sleep.assess(
            duration_hours=duration_hours,
            quality=quality,
            problem_type=problem_type,
            needs_doctor_help=needs_doctor_help,
        )
        self._ctx.results.append(result)
        return f"Sleep Assessment Complete — {result.summary}"

    @llm.ai_callable(
        description=(
            "Assess the patient's appetite. "
            "Call this AFTER asking if appetite is normal in the last week. "
            "If reduced, ask about weight loss. "
            "If weight loss > 5% of body weight, flag for care team."
        )
    )
    async def assess_appetite(
        self,
        appetite_normal: Annotated[bool, llm.TypeInfo(
            description="Whether patient reports normal appetite (True=normal, False=reduced)"
        )],
        weight_loss_percent: Annotated[float, llm.TypeInfo(
            description="Percentage of body weight lost. 0 if no weight loss or appetite is normal."
        )] = 0.0,
    ) -> str:
        """Run appetite assessment and store result."""
        result = self._ctx._appetite.assess(
            appetite_normal=appetite_normal,
            weight_loss_percent=weight_loss_percent,
        )
        self._ctx.results.append(result)

        response = f"Appetite Assessment Complete — {result.summary}"
        if result.requires_care_team:
            response += " Please inform the patient that this will be reported to the care team."
        return response

    @llm.ai_callable(
        description=(
            "Assess a single side effect reported by the patient. "
            "Call this for EACH side effect the patient reports, after determining its severity. "
            "Use the follow-up questions to determine severity level. "
            "Known side effects: oral pain/ulcers, dry mouth, difficulty breathing, "
            "cough, nausea, vomiting, constipation, diarrhea, urinary problems, "
            "tiredness, fever, loss of appetite, skin rash, skin itch, "
            "swelling of hands/feet, pain. For anything else, use 'others'."
        )
    )
    async def assess_side_effect(
        self,
        side_effect_name: Annotated[str, llm.TypeInfo(
            description="Name of the side effect (e.g. 'nausea', 'skin rash', 'tiredness')"
        )],
        severity: Annotated[str, llm.TypeInfo(
            description="Severity level: 'low', 'medium', or 'high'"
        )],
        details: Annotated[str, llm.TypeInfo(
            description="Additional details from the patient about this side effect"
        )] = "",
    ) -> str:
        """Assess a reported side effect and store result."""
        result = self._ctx._side_effects.assess(
            side_effect_name=side_effect_name,
            severity=severity,
            details=details,
        )
        self._ctx.results.append(result)

        response = f"Side Effect Recorded — {side_effect_name}: {severity} severity. "
        if result.requires_care_team:
            response += "HIGH severity — please inform the patient that this will be reported to the care team immediately."
        return response
