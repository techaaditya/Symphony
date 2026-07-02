"""The Search & Rescue agent: maximizes rescues within time-critical windows."""

from __future__ import annotations

from symphony.agents.base_agent import BaseAgent
from symphony.agents.prompts import SEARCH_AND_RESCUE_AGENT_SYSTEM_PROMPT


class SarAgent(BaseAgent):
    name = "sar"
    system_prompt = SEARCH_AND_RESCUE_AGENT_SYSTEM_PROMPT
    allowed_actions = frozenset(
        {"deploy_sar_team", "request_helicopter_transport", "reprioritize_search_zone"}
    )
    expertise_weights = {"sar_team": 1.0, "helicopter": 0.8}
