"""Backend selection for the blackboard store, mirroring `symphony.llm.provider.get_provider`."""

from __future__ import annotations

from symphony.blackboard.base import BlackboardStore
from symphony.blackboard.memory_store import InMemoryBlackboardStore
from symphony.config import BlackboardConfig, get_config


def get_blackboard_store(config: BlackboardConfig | None = None) -> BlackboardStore:
    """Return the active `BlackboardStore`: Tablestore when configured via
    `SYMPHONY_BLACKBOARD=tablestore` and credentials, else the zero-config
    in-memory default.
    """
    cfg = config or get_config().blackboard
    if cfg.is_live:
        from symphony.blackboard.tablestore_store import TablestoreBlackboardStore

        return TablestoreBlackboardStore(
            endpoint=cfg.tablestore_endpoint,
            instance_name=cfg.tablestore_instance_name,
            access_key_id=cfg.tablestore_access_key_id,
            access_key_secret=cfg.tablestore_access_key_secret,
        )
    return InMemoryBlackboardStore()
