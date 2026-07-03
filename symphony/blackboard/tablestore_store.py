"""Alibaba Tablestore-backed blackboard store (doc §11), activated via
`SYMPHONY_BLACKBOARD=tablestore` plus `TABLESTORE_*` env vars
(`symphony.config`).

The blackboard only ever needs to persist one thing — the latest world-state
snapshot — so this backend stores the whole `BlackboardState`, JSON-
serialized, under a single fixed primary key in one table. Real Tablestore
access is opt-in: importing the `tablestore` SDK is deferred to `__init__` so
`symphony.blackboard` stays importable, and the whole test suite runnable,
without the optional `cloud` extra installed.
"""

from __future__ import annotations

import dataclasses
import json
from typing import Any

from symphony.blackboard.base import BlackboardStore
from symphony.models import (
    BlackboardState,
    CasualtyReport,
    ResourcePools,
    Tower,
    TrappedReport,
    Zone,
)

TABLE_NAME = "symphony_blackboard"
_PRIMARY_KEY_COLUMN = "id"
_PRIMARY_KEY_VALUE = "current"
_STATE_COLUMN = "state_json"


class TablestoreBlackboardStore(BlackboardStore):
    """Persists the current `BlackboardState` snapshot to a single Tablestore row."""

    def __init__(
        self, endpoint: str, instance_name: str, access_key_id: str, access_key_secret: str
    ) -> None:
        try:
            import tablestore
        except ImportError as exc:
            raise RuntimeError(
                "TablestoreBlackboardStore requires the optional 'cloud' extra: "
                "pip install -e '.[cloud]'"
            ) from exc
        self._tablestore = tablestore
        self._client = tablestore.OTSClient(
            endpoint, access_key_id, access_key_secret, instance_name
        )

    def load(self) -> BlackboardState | None:
        primary_key = [(_PRIMARY_KEY_COLUMN, _PRIMARY_KEY_VALUE)]
        _consumed, row, _next_token = self._client.get_row(TABLE_NAME, primary_key, None, None)
        if row is None:
            return None
        columns = {name: value for name, value, *_rest in row[1]}
        return _state_from_dict(json.loads(columns[_STATE_COLUMN]))

    def save(self, state: BlackboardState) -> None:
        tablestore = self._tablestore
        primary_key = [(_PRIMARY_KEY_COLUMN, _PRIMARY_KEY_VALUE)]
        attribute_columns = [(_STATE_COLUMN, json.dumps(dataclasses.asdict(state), default=str))]
        row = tablestore.Row(primary_key, attribute_columns)
        condition = tablestore.Condition(tablestore.RowExistenceExpectation.IGNORE)
        self._client.put_row(TABLE_NAME, row, condition)


def _state_from_dict(data: dict[str, Any]) -> BlackboardState:
    return BlackboardState(
        tick=data["tick"],
        zones={zone_id: Zone(**z) for zone_id, z in data["zones"].items()},
        resources=ResourcePools(**data["resources"]),
        towers={tower_id: Tower(**t) for tower_id, t in data["towers"].items()},
        casualties=[CasualtyReport(**c) for c in data.get("casualties", [])],
        trapped=[TrappedReport(**t) for t in data.get("trapped", [])],
    )
