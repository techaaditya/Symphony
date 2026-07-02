"""The Comms agent: maximizes communications network coverage."""

from __future__ import annotations

from symphony.agents.base_agent import BaseAgent
from symphony.agents.prompts import COMMS_AGENT_SYSTEM_PROMPT


class CommsAgent(BaseAgent):
    name = "comms"
    system_prompt = COMMS_AGENT_SYSTEM_PROMPT
    allowed_actions = frozenset(
        {"repair_tower", "deploy_mobile_tower", "reprioritize_repair_order"}
    )
    expertise_weights = {"comms_tower": 1.0}
