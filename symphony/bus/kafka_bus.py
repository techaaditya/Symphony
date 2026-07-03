"""ApsaraMQ-for-Kafka event bus (doc §11), activated via `SYMPHONY_BUS=kafka`
plus `KAFKA_*` env vars (`symphony.config`).

Publishes each `SimEvent` as a JSON message to a fixed topic; `drain()`
consumes and returns everything received since the last drain — the same
"buffer then flush" contract `InMemoryEventBus` honors, so callers never need
to know which backend is live. Real Kafka access is opt-in: importing
`kafka-python` is deferred to `__init__` so `symphony.bus` stays importable,
and the whole test suite runnable, without the optional `bus` extra installed.
"""

from __future__ import annotations

import dataclasses
import json
from typing import Any

from symphony.bus.base import EventBus
from symphony.models import SimEvent


class KafkaEventBus(EventBus):
    """Publishes `SimEvent`s to ApsaraMQ for Kafka and drains what's arrived."""

    def __init__(
        self,
        bootstrap_servers: str,
        topic: str,
        *,
        sasl_username: str = "",
        sasl_password: str = "",
    ) -> None:
        try:
            from kafka import KafkaConsumer, KafkaProducer
        except ImportError as exc:
            raise RuntimeError(
                "KafkaEventBus requires the optional 'bus' extra: pip install -e '.[bus]'"
            ) from exc

        self.topic = topic
        security_kwargs: dict[str, Any] = {}
        if sasl_username and sasl_password:
            security_kwargs = {
                "security_protocol": "SASL_SSL",
                "sasl_mechanism": "PLAIN",
                "sasl_plain_username": sasl_username,
                "sasl_plain_password": sasl_password,
            }

        self._producer = KafkaProducer(
            bootstrap_servers=bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            **security_kwargs,
        )
        # A short poll timeout so drain() returns promptly once everything
        # currently available has been consumed, rather than blocking for
        # more messages that may never arrive this tick.
        self._consumer = KafkaConsumer(
            topic,
            bootstrap_servers=bootstrap_servers,
            value_deserializer=lambda v: json.loads(v.decode("utf-8")),
            auto_offset_reset="earliest",
            consumer_timeout_ms=200,
            **security_kwargs,
        )

    def publish(self, event: SimEvent) -> None:
        self._producer.send(self.topic, dataclasses.asdict(event))
        self._producer.flush()

    def drain(self) -> list[SimEvent]:
        return [SimEvent(**message.value) for message in self._consumer]
