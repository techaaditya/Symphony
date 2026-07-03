"""Interface-conformance tests for the cloud service adapters (doc §11):
Tablestore blackboard and ApsaraMQ/Kafka event bus. Real backends are
exercised against lightweight fakes standing in for their SDKs -- no live
cloud account or broker needed -- and the "extra not installed" degradation
path is verified by forcing the import to fail regardless of whether the
optional packages happen to be installed in this environment.
"""

from __future__ import annotations

import builtins
import sys
import types
from typing import Any

import pytest

from symphony.blackboard.factory import get_blackboard_store
from symphony.blackboard.memory_store import InMemoryBlackboardStore
from symphony.bus.factory import get_event_bus
from symphony.bus.memory_bus import InMemoryEventBus
from symphony.config import BlackboardConfig, BusConfig
from symphony.models import BlackboardState, ResourcePools, SimEvent, Tower, Zone


def _force_import_error(monkeypatch: pytest.MonkeyPatch, module_name: str) -> None:
    real_import = builtins.__import__

    def fake_import(name: str, *args: Any, **kwargs: Any) -> Any:
        if name == module_name or name.startswith(module_name + "."):
            raise ImportError(f"simulated missing {module_name}")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)


# -- factory defaults (no config, no cloud extras needed) --------------------


def test_get_blackboard_store_defaults_to_memory() -> None:
    assert isinstance(get_blackboard_store(BlackboardConfig()), InMemoryBlackboardStore)


def test_get_event_bus_defaults_to_memory() -> None:
    assert isinstance(get_event_bus(BusConfig()), InMemoryEventBus)


# -- graceful failure without the optional extras installed ------------------


def test_tablestore_store_raises_a_helpful_error_without_the_cloud_extra(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _force_import_error(monkeypatch, "tablestore")
    from symphony.blackboard.tablestore_store import TablestoreBlackboardStore

    with pytest.raises(RuntimeError, match="cloud"):
        TablestoreBlackboardStore("endpoint", "instance", "key", "secret")


def test_kafka_bus_raises_a_helpful_error_without_the_bus_extra(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _force_import_error(monkeypatch, "kafka")
    from symphony.bus.kafka_bus import KafkaEventBus

    with pytest.raises(RuntimeError, match="bus"):
        KafkaEventBus("localhost:9092", "symphony-events")


# -- real behavior against fake SDKs ------------------------------------------


def _install_fake_tablestore(monkeypatch: pytest.MonkeyPatch) -> dict[str, str]:
    """A minimal fake `tablestore` module backing a single in-memory row --
    just enough surface for TablestoreBlackboardStore to round-trip through."""
    storage: dict[str, str] = {}

    class FakeRow:
        def __init__(self, primary_key: Any, attribute_columns: Any) -> None:
            self.primary_key = primary_key
            self.attribute_columns = attribute_columns

    class FakeCondition:
        def __init__(self, expectation: Any) -> None:
            self.expectation = expectation

    class FakeRowExistenceExpectation:
        IGNORE = "IGNORE"

    class FakeOTSClient:
        def __init__(
            self, endpoint: str, access_key_id: str, access_key_secret: str, instance_name: str
        ) -> None:
            pass

        def put_row(self, table_name: str, row: FakeRow, condition: FakeCondition) -> None:
            storage["state_json"] = dict(row.attribute_columns)["state_json"]

        def get_row(
            self, table_name: str, primary_key: Any, columns_to_get: Any, max_version: Any
        ) -> tuple[Any, Any, Any]:
            if "state_json" not in storage:
                return None, None, None
            row = (primary_key, [("state_json", storage["state_json"], 0)])
            return None, row, None

    fake_module = types.SimpleNamespace(
        OTSClient=FakeOTSClient,
        Row=FakeRow,
        Condition=FakeCondition,
        RowExistenceExpectation=FakeRowExistenceExpectation,
    )
    monkeypatch.setitem(sys.modules, "tablestore", fake_module)
    return storage


def test_tablestore_store_round_trips_a_blackboard_state(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_fake_tablestore(monkeypatch)
    from symphony.blackboard.tablestore_store import TablestoreBlackboardStore

    store = TablestoreBlackboardStore("endpoint", "instance", "key", "secret")
    assert store.load() is None

    state = BlackboardState(
        tick=3,
        zones={"zone-1": Zone(id="zone-1", name="Z", lat=1.0, lng=2.0)},
        resources=ResourcePools(
            helicopters=1, medic_teams=1, sar_teams=1, comms_towers=1, budget_remaining=1000.0
        ),
        towers={"tower-1": Tower(id="tower-1", zone_id="zone-1")},
    )
    store.save(state)

    assert store.load() == state


def test_get_blackboard_store_selects_tablestore_when_live(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_fake_tablestore(monkeypatch)
    from symphony.blackboard.tablestore_store import TablestoreBlackboardStore

    config = BlackboardConfig(backend="tablestore", tablestore_endpoint="https://example")
    store = get_blackboard_store(config)

    assert isinstance(store, TablestoreBlackboardStore)


def _install_fake_kafka(monkeypatch: pytest.MonkeyPatch) -> list[bytes]:
    """A minimal fake `kafka` module: publish() appends to a shared queue,
    and iterating the fake consumer drains that same queue -- no network."""
    sent: list[bytes] = []

    class FakeMessage:
        def __init__(self, value: Any) -> None:
            self.value = value

    class FakeKafkaProducer:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            self._value_serializer = kwargs.get("value_serializer")

        def send(self, topic: str, value: Any) -> None:
            sent.append(self._value_serializer(value) if self._value_serializer else value)

        def flush(self) -> None:
            pass

    class FakeKafkaConsumer:
        def __init__(self, topic: str, *args: Any, **kwargs: Any) -> None:
            self._value_deserializer = kwargs.get("value_deserializer")

        def __iter__(self):
            while sent:
                raw = sent.pop(0)
                value = self._value_deserializer(raw) if self._value_deserializer else raw
                yield FakeMessage(value)

    fake_module = types.SimpleNamespace(
        KafkaProducer=FakeKafkaProducer, KafkaConsumer=FakeKafkaConsumer
    )
    monkeypatch.setitem(sys.modules, "kafka", fake_module)
    return sent


def test_kafka_bus_round_trips_published_events(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_fake_kafka(monkeypatch)
    from symphony.bus.kafka_bus import KafkaEventBus

    bus = KafkaEventBus("localhost:9092", "symphony-events")
    event = SimEvent(tick=1, type="fire_spread", zone_id="zone-1", payload={"intensity_delta": 0.2})
    bus.publish(event)

    assert bus.drain() == [event]


def test_get_event_bus_selects_kafka_when_live(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_fake_kafka(monkeypatch)
    from symphony.bus.kafka_bus import KafkaEventBus

    config = BusConfig(backend="kafka", bootstrap_servers="broker:9092")
    bus = get_event_bus(config)

    assert isinstance(bus, KafkaEventBus)
