"""The Finance agent: minimizes spend subject to a minimum-objectives floor.

Holds a limited veto (`Proposal.veto` / `veto_target`) over budget-exceeding
proposals, enforced deterministically by the Parliament Protocol (a later
phase) — overridable only by unanimous vote of the other four agents.
"""

from __future__ import annotations

from symphony.agents.base_agent import BaseAgent
from symphony.agents.prompts import FINANCE_AGENT_SYSTEM_PROMPT


class FinanceAgent(BaseAgent):
    name = "finance"
    system_prompt = FINANCE_AGENT_SYSTEM_PROMPT
    allowed_actions = frozenset({"flag_budget_risk"})
    expertise_weights = {"budget": 1.0}
