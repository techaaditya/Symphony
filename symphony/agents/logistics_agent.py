"""The Logistics agent: maximizes coverage speed, minimizes travel time."""

from __future__ import annotations

from symphony.agents.base_agent import BaseAgent
from symphony.agents.prompts import LOGISTICS_AGENT_SYSTEM_PROMPT


class LogisticsAgent(BaseAgent):
    name = "logistics"
    system_prompt = LOGISTICS_AGENT_SYSTEM_PROMPT
    allowed_actions = frozenset({"route_helicopter", "route_ground_vehicle", "reprioritize_route"})
    expertise_weights = {"helicopter": 1.0, "ground_vehicle": 0.9}
