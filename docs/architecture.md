# Architecture

## System overview

```mermaid
flowchart TB
    subgraph Sim["Simulator (symphony/simulator)"]
        Scenario["wildfire_v3.json\n(fixed event schedule)"]
        Engine["Simulator.step()\nseeded jitter"]
        Scenario --> Engine
    end

    Engine -->|"SimEvent"| Bus["Event bus\n(in-memory / ApsaraMQ-Kafka)"]
    Engine -->|"BlackboardState"| Board["Blackboard store\n(in-memory / Tablestore)"]

    subgraph Parliament["Parliament Protocol (symphony/protocol)"]
        direction TB
        Propose["OPEN_ROUND\nfive agents propose"]
        Conflict["CONFLICT_CHECK"]
        Debate["DEBATE\n(bounded, ≤3 rounds)"]
        Vote["VOTE\nexpertise-weighted"]
        Escalate["ESCALATE\n(Coordinator rules)"]
        Commit["COMMIT\n(Finance veto enforced)"]
        Propose --> Conflict --> Debate --> Vote --> Escalate --> Commit
        Conflict -.no conflict.-> Commit
    end

    Board --> Propose
    Agents["Logistics · Medical · Comms\nFinance · Search & Rescue\n(symphony/agents)"] <-->|"LLMProvider\n(Mock / Qwen)"| Propose
    Coordinator["Coordinator"] <-->|"LLMProvider"| Escalate
    Commit --> Board

    Commit --> Ledger["Ledger\n(JSONL, symphony/ledger)"]
    Conflict -->|"per conflict"| Graph["Conflict Graph writer\n(JSON file / Neo4j)"]

    subgraph API["REST API (symphony/api, FastAPI)"]
        SimEP["/sim/start · /sim/tick\n/sim/ledger · /sim/stream (SSE)"]
        BenchEP["/benchmark/run · /benchmark/compare"]
        ConflictEP["/conflicts/graph"]
    end

    Ledger --> SimEP
    Board --> SimEP
    Graph --> ConflictEP

    subgraph Bench["Benchmark harness (symphony/benchmark)"]
        Society["run_symphony_society()\n(Parliament Protocol)"]
        Baseline["run_single_agent_baseline()\n(one generalist call/tick)"]
        Society --> BenchEP
        Baseline --> BenchEP
    end

    subgraph Dashboard["Dashboard (Next.js)"]
        Live["Live: disaster map + agent graph"]
        LedgerView["Ledger replay"]
        ConflictView["Conflict Graph Explorer"]
        BenchView["Benchmark chart"]
    end

    SimEP -->|"fetch / SSE"| Live
    SimEP -->|"fetch"| LedgerView
    ConflictEP -->|"fetch"| ConflictView
    BenchEP -->|"fetch"| BenchView
```

## Design principle

> **Agents propose, deterministic code adjudicates.**

Every agent's *proposal* comes from an LLM call (`LLMProvider.complete`). Everything after that —
conflict detection (`_detect_conflicts`), the weighted vote tally (`_run_weighted_vote`), the
Finance veto and its unanimous-override check (`_active_vetoes`), and the commit-to-blackboard
logic (`symphony.protocol.commit`) — is plain, deterministic, unit-tested Python. No LLM call ever
decides who wins a conflict; it only ever produces a proposal, a rebuttal, or a persuasiveness
score that deterministic code then weighs.

## Adapter pattern

Every external dependency sits behind an interface with a zero-config local default and an opt-in
live backend, selected by `symphony/config.py` reading environment variables:

| Concern | Interface | Local default | Live backend |
|---|---|---|---|
| LLM | `LLMProvider` | `MockProvider` (seeded, deterministic) | `QwenProvider` (DashScope) |
| Event bus | `EventBus` | `InMemoryEventBus` | `KafkaEventBus` (ApsaraMQ for Kafka) |
| Blackboard | `BlackboardStore` | `InMemoryBlackboardStore` | `TablestoreBlackboardStore` |
| Conflict graph | `ConflictGraphWriter` | `JsonConflictGraphWriter` | `Neo4jConflictGraphWriter` |

This is why the full test suite (87 tests) and every CLI/API path run with zero API keys and zero
token cost by default — and why the exact same code path runs unmodified against real Alibaba
Cloud services once `SYMPHONY_LLM=qwen` / `SYMPHONY_BUS=kafka` / `SYMPHONY_BLACKBOARD=tablestore` /
`NEO4J_URI=...` are set (see `infra/alibaba-cloud/DEPLOY_RUNBOOK.md`).

## Deployment topology (Alibaba Cloud)

```mermaid
flowchart LR
    subgraph ECS["ECS instance"]
        Neo4jC["Neo4j container\n(docker run, doc §22)"]
        ApiC["api container\n(docker compose)"]
        DashC["dashboard container"]
    end
    Browser["Browser / judge"] -->|":3000"| DashC
    Browser -->|":8000"| ApiC
    Browser -->|":7474"| Neo4jC
    DashC -->|"fetch/SSE :8000"| ApiC
    ApiC -->|"bolt :7687"| Neo4jC
    ApiC -->|"Kafka protocol"| Kafka["ApsaraMQ for Kafka\n(managed instance)"]
    ApiC -->|"OTS API"| Tablestore["Tablestore\n(managed instance)"]
```

The ECS instance hosts Neo4j directly (per the design doc's exact `docker run` command) and also
runs the `api`/`dashboard` containers via `docker-compose.prod.yml`; Tablestore and ApsaraMQ for
Kafka are separate managed services the API reaches over the network. See
`infra/alibaba-cloud/terraform/` for the resource definitions and
`infra/alibaba-cloud/DEPLOY_RUNBOOK.md` for the full deploy sequence.
