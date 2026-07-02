# Symphony — Multi-Agent Crisis Response Society

**Hackathon:** Global AI Hackathon Series with Qwen Cloud · **Track:** Agent Society

A simulated disaster (wildfire) unfolds over discrete time-steps. Five specialist agents —
Logistics, Medical, Comms, Finance, Search & Rescue — collaboratively allocate scarce resources
(helicopters, medics, comms towers, budget), negotiating conflicts through a structured
**Parliament Protocol** (propose → debate → vote → commit), with unresolved deadlocks escalated to
a Coordinator. The full deliberation is logged to a ledger and explorable as a graph. Symphony's
headline proof point is a measured benchmark showing the five-agent society outperforming a
single-agent baseline on identical scenarios.

## Design principle

> **Agents propose, deterministic code adjudicates.**

Every agent's *proposal* comes from an LLM. Conflict detection, vote tallying, veto enforcement,
and commit logic are all plain deterministic Python — never re-delegated to a generative model.

## Runs offline, by default

Every external dependency (LLM, event bus, blackboard store, conflict graph) sits behind a
pluggable interface with a local, zero-config default:

| Concern | Default (no config) | Live backend (opt-in via env) |
|---|---|---|
| LLM | Deterministic `MockProvider` | Qwen via DashScope (`SYMPHONY_LLM=qwen`) |
| Event bus | In-memory | ApsaraMQ for Kafka (`SYMPHONY_BUS=kafka`) |
| Blackboard | In-memory | Alibaba Tablestore (`SYMPHONY_BLACKBOARD=tablestore`) |
| Conflict graph | Local JSON file | Neo4j (`NEO4J_URI=...`) |

The whole system — simulator, agents, protocol, ledger, benchmark, and the full test suite — runs
with **zero API keys and zero token cost** via the mock LLM. See [`.env.example`](.env.example)
for every adapter setting.

## Quickstart

> Full quickstart lands as each phase of the build is completed. Current status: repo scaffold.

```bash
pip install -e ".[dev]"
pytest -q
```

Once the simulator and CLI land (build phases 1–6):

```bash
symphony sim --scenario wildfire_v3 --seed 42
symphony benchmark --n 5
```

## Repository layout

```
symphony/
├── symphony/            # Python backend package
│   ├── config.py        # env-driven adapter selection (this phase)
│   ├── blackboard/       bus/       simulator/       llm/
│   ├── agents/          protocol/  ledger/          benchmark/
│   └── api/              # FastAPI server (later phase)
├── dashboard/            # Next.js dashboard (later phase)
├── infra/alibaba-cloud/  # Terraform + deploy runbook (later phase)
├── docs/                 # architecture, demo script, self-audit (later phase)
└── tests/
```

## Responsible AI

See [`responsible-ai.md`](responsible-ai.md) for model choices, data sources, bias and limitation
considerations, failure-case mitigations, and an explicit statement of what this system is not.

## License

MIT — see [`LICENSE`](LICENSE).
