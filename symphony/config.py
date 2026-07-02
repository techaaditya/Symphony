"""Environment-driven adapter selection.

Every external dependency in Symphony (LLM, event bus, blackboard store,
conflict graph) sits behind an interface with a local, zero-config default.
This module reads the environment once and exposes a typed `SymphonyConfig`
that the rest of the codebase uses to decide which concrete backend to
construct. Nothing here imports a cloud SDK directly — that keeps `pip
install -e .` and the test suite runnable with no optional dependencies
installed.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    return int(raw) if raw else default


@dataclass(frozen=True)
class LLMConfig:
    """Selects and configures the LLM backend (symphony.llm.provider)."""

    provider: str = "mock"  # "mock" | "qwen"
    mock_seed: int = 42
    dashscope_api_key: str = ""
    dashscope_base_url: str = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
    specialist_model: str = "qwen-turbo"
    coordinator_model: str = "qwen-max"

    @property
    def is_live(self) -> bool:
        return self.provider == "qwen" and bool(self.dashscope_api_key)


@dataclass(frozen=True)
class BusConfig:
    """Selects and configures the event bus backend (symphony.bus)."""

    backend: str = "memory"  # "memory" | "kafka"
    bootstrap_servers: str = ""
    topic_events: str = "symphony-events"
    sasl_username: str = ""
    sasl_password: str = ""

    @property
    def is_live(self) -> bool:
        return self.backend == "kafka" and bool(self.bootstrap_servers)


@dataclass(frozen=True)
class BlackboardConfig:
    """Selects and configures the blackboard backend (symphony.blackboard)."""

    backend: str = "memory"  # "memory" | "tablestore"
    tablestore_endpoint: str = ""
    tablestore_instance_name: str = ""
    tablestore_access_key_id: str = ""
    tablestore_access_key_secret: str = ""

    @property
    def is_live(self) -> bool:
        return self.backend == "tablestore" and bool(self.tablestore_endpoint)


@dataclass(frozen=True)
class ConflictGraphConfig:
    """Selects and configures the conflict-graph backend (symphony.protocol.conflict_graph)."""

    neo4j_uri: str = ""
    neo4j_user: str = "neo4j"
    neo4j_password: str = ""
    json_path: str = "./conflict_graph.json"

    @property
    def backend(self) -> str:
        return "neo4j" if self.neo4j_uri else "json"

    @property
    def is_live(self) -> bool:
        return bool(self.neo4j_uri)


@dataclass(frozen=True)
class SymphonyConfig:
    """Top-level configuration, assembled once from the environment."""

    llm: LLMConfig = field(default_factory=LLMConfig)
    bus: BusConfig = field(default_factory=BusConfig)
    blackboard: BlackboardConfig = field(default_factory=BlackboardConfig)
    conflict_graph: ConflictGraphConfig = field(default_factory=ConflictGraphConfig)
    ledger_path: str = "./ledger.jsonl"
    api_cors_origins: str = "http://localhost:3000"

    @classmethod
    def from_env(cls) -> SymphonyConfig:
        return cls(
            llm=LLMConfig(
                provider=_env("SYMPHONY_LLM", "mock"),
                mock_seed=_env_int("SYMPHONY_MOCK_SEED", 42),
                dashscope_api_key=_env("DASHSCOPE_API_KEY"),
                dashscope_base_url=_env(
                    "DASHSCOPE_BASE_URL",
                    "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
                ),
                specialist_model=_env("QWEN_SPECIALIST_MODEL", "qwen-turbo"),
                coordinator_model=_env("QWEN_COORDINATOR_MODEL", "qwen-max"),
            ),
            bus=BusConfig(
                backend=_env("SYMPHONY_BUS", "memory"),
                bootstrap_servers=_env("KAFKA_BOOTSTRAP_SERVERS"),
                topic_events=_env("KAFKA_TOPIC_EVENTS", "symphony-events"),
                sasl_username=_env("KAFKA_SASL_USERNAME"),
                sasl_password=_env("KAFKA_SASL_PASSWORD"),
            ),
            blackboard=BlackboardConfig(
                backend=_env("SYMPHONY_BLACKBOARD", "memory"),
                tablestore_endpoint=_env("TABLESTORE_ENDPOINT"),
                tablestore_instance_name=_env("TABLESTORE_INSTANCE_NAME"),
                tablestore_access_key_id=_env("TABLESTORE_ACCESS_KEY_ID"),
                tablestore_access_key_secret=_env("TABLESTORE_ACCESS_KEY_SECRET"),
            ),
            conflict_graph=ConflictGraphConfig(
                neo4j_uri=_env("NEO4J_URI"),
                neo4j_user=_env("NEO4J_USER", "neo4j"),
                neo4j_password=_env("NEO4J_PASSWORD"),
                json_path=_env("SYMPHONY_CONFLICT_GRAPH_JSON_PATH", "./conflict_graph.json"),
            ),
            ledger_path=_env("SYMPHONY_LEDGER_PATH", "./ledger.jsonl"),
            api_cors_origins=_env("SYMPHONY_API_CORS_ORIGINS", "http://localhost:3000"),
        )


@lru_cache(maxsize=1)
def get_config() -> SymphonyConfig:
    """Return the process-wide config, parsed from the environment once."""
    return SymphonyConfig.from_env()
