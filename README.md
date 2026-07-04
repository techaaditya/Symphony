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

### Python core only (no Docker, zero cost)

```bash
pip install -e ".[dev]"
pytest -q                                        # 87+ tests, mock LLM, no network

symphony sim --scenario wildfire_v3 --seed 42     # one seeded run, printed to the terminal
symphony benchmark --n 5                          # society vs. single-agent, mean/SD table
```

### Full stack (dashboard + REST API + real Neo4j + real Kafka)

```bash
pip install -e ".[api]"                           # only needed if you run the API outside Docker
cp .env.example .env                              # optional: tune adapters, still zero-cost by default
make up                                           # builds and starts neo4j, redpanda, api, dashboard
make seed                                         # drives one real scenario through the running stack
```

- Dashboard: <http://localhost:3000> (live map + agent graph, ledger replay, Conflict Graph
  Explorer, benchmark chart)
- API docs: <http://localhost:8000/docs>
- Neo4j browser: <http://localhost:7474> (`neo4j` / `symphony123` by default — see `Makefile`)

`make down` stops the stack; `make clean` also wipes the Neo4j volume for a clean-slate demo.
See the [`Makefile`](Makefile) for the rest (`logs`, `build`, `test`, `bench`).

### Live Qwen run (optional, real API calls)

```bash
SYMPHONY_LLM=qwen DASHSCOPE_API_KEY=... symphony sim --scenario wildfire_v3 --seed 42
```

## Repository layout

```
symphony/
├── symphony/             # Python backend package
│   ├── config.py         # env-driven adapter selection
│   ├── blackboard/        bus/        simulator/        llm/
│   ├── agents/           protocol/   ledger/            benchmark/
│   └── api/              # FastAPI server + SSE stream (doc §12)
├── dashboard/            # Next.js dashboard: live map, agent graph, ledger replay,
│                         # Conflict Graph Explorer, benchmark chart
├── docker-compose.yml    # local Neo4j + Redpanda + api + dashboard
├── infra/alibaba-cloud/  # Terraform + deploy runbook (later phase)
├── docs/                 # architecture, demo script, self-audit (later phase)
└── tests/
```

## Responsible AI

See [`responsible-ai.md`](responsible-ai.md) for model choices, data sources, bias and limitation
considerations, failure-case mitigations, and an explicit statement of what this system is not.

## License

MIT — see [`LICENSE`](LICENSE).
