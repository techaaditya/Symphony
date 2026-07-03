"""Backend selection for the event bus, mirroring `symphony.llm.provider.get_provider`."""

from __future__ import annotations

from symphony.bus.base import EventBus
from symphony.bus.memory_bus import InMemoryEventBus
from symphony.config import BusConfig, get_config


def get_event_bus(config: BusConfig | None = None) -> EventBus:
    """Return the active `EventBus`: ApsaraMQ for Kafka when configured via
    `SYMPHONY_BUS=kafka` and a broker address, else the zero-config in-memory
    default.
    """
    cfg = config or get_config().bus
    if cfg.is_live:
        from symphony.bus.kafka_bus import KafkaEventBus

        return KafkaEventBus(
            bootstrap_servers=cfg.bootstrap_servers,
            topic=cfg.topic_events,
            sasl_username=cfg.sasl_username,
            sasl_password=cfg.sasl_password,
        )
    return InMemoryEventBus()
