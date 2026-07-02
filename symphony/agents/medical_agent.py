"""The Medical agent: maximizes lives saved, minimizes untreated-casualty time."""

from __future__ import annotations

from symphony.agents.base_agent import BaseAgent
from symphony.agents.prompts import MEDICAL_AGENT_SYSTEM_PROMPT


class MedicalAgent(BaseAgent):
    name = "medical"
    system_prompt = MEDICAL_AGENT_SYSTEM_PROMPT
    allowed_actions = frozenset(
        {"deploy_medic_team", "request_helicopter_transport", "triage_priority_change"}
    )
    expertise_weights = {"medic_team": 1.0, "helicopter": 0.8}
