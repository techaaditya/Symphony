"""Tests for the REST API (doc §12): a full sim/start -> tick -> ledger ->
conflicts/graph flow, plus the benchmark endpoints. Requires the optional
`api` extra (`pip install -e ".[api]"`); skipped entirely otherwise, since
the rest of Symphony must stay runnable and testable without it.
"""

from __future__ import annotations

import pytest

fastapi = pytest.importorskip("fastapi")

from fastapi.testclient import TestClient  # noqa: E402

from symphony.api.app import app  # noqa: E402
from symphony.api.state import reset_registry  # noqa: E402


@pytest.fixture(autouse=True)
def _clear_registry():
    reset_registry()
    yield
    reset_registry()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_sim_start_returns_a_session(client: TestClient) -> None:
    response = client.post("/sim/start", json={"scenario_id": "wildfire_v3", "seed": 42})

    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "society"
    assert body["ticks_total"] == 20
    assert body["sim_id"]


def test_sim_tick_advances_and_returns_round_payload(client: TestClient) -> None:
    sim_id = client.post("/sim/start", json={"scenario_id": "wildfire_v3", "seed": 42}).json()[
        "sim_id"
    ]

    response = client.post("/sim/tick", json={"sim_id": sim_id})

    assert response.status_code == 200
    body = response.json()
    assert body["tick"] == 1
    assert body["finished"] is False
    assert {p["agent"] for p in body["result"]["proposals"]} == {
        "logistics",
        "medical",
        "comms",
        "finance",
        "sar",
    }


def test_sim_tick_unknown_sim_id_returns_404(client: TestClient) -> None:
    response = client.post("/sim/tick", json={"sim_id": "does-not-exist"})
    assert response.status_code == 404


def test_sim_tick_past_the_end_returns_409(client: TestClient) -> None:
    sim_id = client.post("/sim/start", json={"scenario_id": "wildfire_v3", "seed": 42}).json()[
        "sim_id"
    ]
    for _ in range(20):
        assert client.post("/sim/tick", json={"sim_id": sim_id}).status_code == 200

    response = client.post("/sim/tick", json={"sim_id": sim_id})
    assert response.status_code == 409


def test_sim_ledger_accumulates_one_entry_per_tick(client: TestClient) -> None:
    sim_id = client.post("/sim/start", json={"scenario_id": "wildfire_v3", "seed": 42}).json()[
        "sim_id"
    ]
    for _ in range(3):
        client.post("/sim/tick", json={"sim_id": sim_id})

    response = client.get("/sim/ledger", params={"sim_id": sim_id})

    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "society"
    assert len(body["entries"]) == 3
    assert [entry["tick"] for entry in body["entries"]] == [1, 2, 3]


def test_single_agent_mode_ledger_records_baseline_decisions(client: TestClient) -> None:
    sim_id = client.post(
        "/sim/start", json={"scenario_id": "wildfire_v3", "seed": 42, "mode": "single_agent"}
    ).json()["sim_id"]
    client.post("/sim/tick", json={"sim_id": sim_id})

    response = client.get("/sim/ledger", params={"sim_id": sim_id})

    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "single_agent"
    assert len(body["entries"]) == 1
    assert "committed" in body["entries"][0]


def test_conflicts_graph_reflects_a_real_conflict(client: TestClient) -> None:
    # wildfire_v3 seed=42 reliably produces a Medical-vs-SAR helicopter
    # conflict by tick 4 (casualty_report + trapped_report both land on
    # zone-2 at tick 4) -- the same scenario/seed relied on elsewhere.
    sim_id = client.post("/sim/start", json={"scenario_id": "wildfire_v3", "seed": 42}).json()[
        "sim_id"
    ]
    for _ in range(4):
        client.post("/sim/tick", json={"sim_id": sim_id})

    response = client.get("/conflicts/graph", params={"sim_id": sim_id, "agent": "medical"})

    assert response.status_code == 200
    body = response.json()
    assert any(edge["resource"] == "helicopter" for edge in body["edges"])
    assert {a["name"] for a in body["agents"]} >= {"medical"}


def test_conflicts_graph_unknown_sim_id_returns_404(client: TestClient) -> None:
    response = client.get("/conflicts/graph", params={"sim_id": "nope", "agent": "medical"})
    assert response.status_code == 404


def test_benchmark_run_returns_mean_sd_shape(client: TestClient) -> None:
    response = client.post(
        "/benchmark/run",
        json={"scenario_id": "wildfire_v3", "seed": 1, "n_trials": 1, "mode": "single_agent"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "single_agent"
    assert "mean" in body["objectives_met_pct"]


def test_benchmark_compare_returns_both_modes(client: TestClient) -> None:
    response = client.post(
        "/benchmark/compare", json={"scenario_id": "wildfire_v3", "seed": 1, "n_trials": 1}
    )

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"single_agent", "society"}


def test_sim_stream_emits_one_tick_event_per_tick(client: TestClient) -> None:
    sim_id = client.post("/sim/start", json={"scenario_id": "wildfire_v3", "seed": 42}).json()[
        "sim_id"
    ]

    stream_params = {"sim_id": sim_id, "interval_ms": 0}
    with client.stream("GET", "/sim/stream", params=stream_params) as response:
        assert response.status_code == 200
        events = [line for line in response.iter_lines() if line.startswith("event:")]

    assert events.count("event: tick") == 20
    assert events[-1] == "event: done"
