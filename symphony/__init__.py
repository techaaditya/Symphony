"""Symphony — a multi-agent crisis-response society.

Five specialist agents and a Coordinator negotiate scarce disaster-response
resources through the Parliament Protocol (propose -> debate -> vote ->
escalate -> commit). Every external dependency (LLM, event bus, blackboard
store, conflict graph) is a pluggable adapter with a local, zero-config
default; see `symphony.config` for how the active backend is selected.

Design principle: agents propose, deterministic code adjudicates.
"""

__version__ = "0.1.0"
