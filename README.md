# Symphony — Multi-Agent Crisis Response Society

**Hackathon:** Global AI Hackathon Series with Qwen Cloud · **Track:** Agent Society

A simulated disaster (wildfire) unfolds over discrete time-steps. Five specialist agents —
Logistics, Medical, Comms, Finance, Search & Rescue — collaboratively allocate scarce resources
(helicopters, medics, comms towers, budget), negotiating conflicts through a structured
**Parliament Protocol** (propose → debate → vote → commit), with unresolved deadlocks escalated to
a Coordinator. The full deliberation is logged to a ledger and explorable as a graph.

Symphony's headline proof point is a measured benchmark ([below](#benchmark-measured-results))
comparing the five-agent society against a single-agent baseline on identical scenarios and seeds
— reported honestly, including a real tradeoff the society makes that the baseline can't: an
explicit, auditable Finance veto that protects the operating budget at the cost of some unmet
objectives, versus a baseline with zero budget governance at all.

**Beyond disaster response:** the same shape — several specialists with different stakes
contending for a shared pool of scarce, indivisible resources, needing an auditable
conflict-resolution process rather than a single opaque decision-maker — applies directly to
supply-chain allocation during a shortage, multi-team incident response, and cross-department
budget arbitration. The Parliament Protocol (propose → debate → vote → escalate → commit) and the
Finance-style veto are domain-agnostic; only the five agents' prompts and `wildfire_v3.json`'s
scenario data are wildfire-specific.

## Design principle

> **Agents propose, deterministic code adjudicates.**

Every agent's *proposal* comes from an LLM. Conflict detection, vote tallying, veto enforcement,
and commit logic are all plain deterministic Python — never re-delegated to a generative model.

## Runs offline, by default

Every external dependency (LLM, event bus, blackboard store, conflict graph) sits behind a
pluggable interface with a local, zero-config default:

| Concern | Default (no config) | Live backend (opt-in via env) |
| --- | --- | --- |
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

## The Parliament Protocol, worked from a real run

State machine: `OPEN_ROUND → CONFLICT_CHECK → DEBATE → VOTE → ESCALATE → COMMIT`
(`symphony/protocol/parliament.py`). Every proposal in this section is real output from
`symphony sim --scenario wildfire_v3 --seed 42` — nothing here is hand-constructed.

**The weighted vote formula.** For a conflict on resource `R`, each conflicting side `s` scores:

```
side_score(s) = Σ over every neutral voter v of  v.vote(R) * avg_persuasiveness(v's scores of s's rebuttal)
```

`v.vote(R)` is that agent's fixed expertise weight for resource type `R` (1.0 in its specialty,
0.8/0.9 in an adjacent one, 0.5 baseline elsewhere — `symphony/agents/*.py`); persuasiveness is
averaged across every bounded debate round (`MAX_DEBATE_ROUNDS = 3`). The side with the higher
score wins outright only if it exceeds the runner-up by `MAJORITY_THRESHOLD = 1.2×`; otherwise the
conflict escalates to the Coordinator.

**Tick 10 — a clean, non-escalated vote.** Logistics, Medical and SAR all want the one remaining
helicopter:

| Agent | Rationale | Confidence |
| --- | --- | --- |
| Logistics | "Zone zone-1 fire intensity is 0.58; a helicopter water drop is the fastest way to slow the spread." | 0.93 |
| Medical | "8 critical casualties in zone zone-2; a confirmed casualty's time-criticality outweighs a hypothetical future one." | 0.72 |
| SAR | "2 trapped in zone zone-1 with only 3 ticks left in the rescue window; ground SAR teams are too slow." | 0.77 |

Comms and Finance are the neutral voters (their own weight on "helicopter" is the 0.5 baseline).
Averaging their persuasiveness scores of each side's rebuttal across all 3 rounds and multiplying
by 0.5 gives exactly what the real ledger recorded:

| Side | Comms avg | Finance avg | `side_score` |
| --- | --- | --- | --- |
| Logistics | 0.57 | 0.70 | 0.5·0.57 + 0.5·0.70 = **0.635** |
| Medical | 0.75 | 0.85 | 0.5·0.75 + 0.5·0.85 = **0.800** |
| SAR | 0.39 | 0.76 | 0.5·0.39 + 0.5·0.76 = **0.575** |

Medical wins outright (0.800 > 0.635 × 1.2 = 0.762) — Medical is committed, no escalation needed.

**Tick 15 — escalation and veto together.** Logistics and Medical are tied closely enough
(0.98 vs 0.947 — 0.98 is *not* > 0.947 × 1.2) that the conflict escalates. The Coordinator reviews
the actual debate transcript and rules for Medical. But Finance had already flagged a veto this
same tick:

> "Remaining budget $31,500 is below the $45,000 ceiling needed to safely absorb another
> helicopter deployment this tick." — Finance, confidence 0.64, `veto_target: "helicopter"`

The veto is enforced *after* the Coordinator's ruling — Medical's ruling is overridden and dropped
(`reason: "finance_veto"`), because no unanimous override happened (an override requires all four
non-Finance agents to propose, none abstaining, each at confidence ≥ 0.75 —
`OVERRIDE_CONFIDENCE_THRESHOLD` in `parliament.py`). This is the second, genuinely distinct
conflict-resolution mechanism: a vote can be won and still not committed if Finance vetoes it and
the rest of the society doesn't unanimously overrule that veto.

## Benchmark: measured results

`symphony benchmark --scenario wildfire_v3 --seed 42 --n 20` — the five-agent society against the
single-agent baseline, identical scenario and seeds, 20 trials each. Full raw output committed at
[`symphony/benchmark/results/wildfire_v3_seed42_n20.json`](symphony/benchmark/results/wildfire_v3_seed42_n20.json).

| Metric | Single-agent | Society |
| --- | --- | --- |
| Objectives met | **100.0%** (sd 0.0) | 63.6% (sd 0.0) |
| Time to allocate | 0.005s (sd 0.0005) | 0.066s (sd 0.006) |
| Resource waste | 0.0% (sd 0.0) | 0.0% (sd 0.0) |
| Token cost | **9,399** (sd 1.5) | 247,095 (sd 28.6) |

**Read this honestly, per this project's own transparency commitment:** the society does *not*
simply "win." It resolves 7 of 11 casualty/trapped/tower objectives across every seed (63.6% is
exactly 7⁄11) because Finance's veto starts blocking helicopter allocation once the budget crosses
its safety ceiling partway through the run (see the tick-15 example above) — and once vetoed, that
objective stays unmet for the rest of the scenario. The single-agent baseline has **no budget
governance at all**: it keeps spending against `budget_remaining` with nothing to stop it, so it
"succeeds" at every objective by never once refusing to spend. That's the real, visible tradeoff —
an auditable safety mechanism that costs completed objectives, versus an ungoverned baseline that
completes more objectives with no safety mechanism at all. Token cost is ~26× higher for the
society, from five parallel proposals plus up to three debate rounds per conflict, against the
baseline's one call per tick.

This scenario's specific 220,000-unit starting budget was tuned (from an initial 500,000, which
made every veto path dormant across 20+ seeds — see `docs/self-audit.md`) specifically so the veto
mechanism is reachable in a real run, not just unit-tested in isolation (`tests/test_veto.py`
exercises it directly). `resource_waste_pct` reads 0.0% for both modes on this scenario: a veto
means the resource was never spent at all (recorded as an unmet objective, not a wasted one), and
the mock agents never propose to double-serve an already-resolved objective.

## Architecture

Full system diagram, the adapter pattern, and the Alibaba Cloud deployment topology:
[`docs/architecture.md`](docs/architecture.md).

## Repository layout

```
symphony/
├── symphony/                     # Python backend package
│   ├── config.py                 # env-driven adapter selection
│   ├── blackboard/  bus/  simulator/  llm/
│   ├── agents/      protocol/    ledger/    benchmark/
│   │                                        └── results/wildfire_v3_seed42_n20.json
│   └── api/                      # FastAPI server + SSE stream (doc §12)
├── dashboard/                    # Next.js: live map, agent graph, ledger replay,
│                                 # Conflict Graph Explorer, benchmark chart
├── docker-compose.yml            # local Neo4j + Redpanda + api + dashboard
├── docker-compose.prod.yml       # cloud deploy: api + dashboard against managed services
├── infra/alibaba-cloud/          # Terraform, deploy runbook, deployment-proof checklist
├── docs/                         # architecture, demo script, self-audit
├── scripts/demo_run.py           # scripted demo driver for recording
└── tests/                        # 87 tests, mock LLM, zero network
```

## Demo & self-audit

- [`docs/demo-script.md`](docs/demo-script.md) — the ~3-minute demo storyboard and voiceover.
- [`docs/self-audit.md`](docs/self-audit.md) — an honest self-check against the judging rubric,
  written after the numbers above were measured, not before.
- [`docs/submission-checklist.md`](docs/submission-checklist.md) — the final submission checklist.

## Responsible AI

See [`responsible-ai.md`](responsible-ai.md) for model choices, data sources, bias and limitation
considerations, failure-case mitigations, and an explicit statement of what this system is not.

## License

MIT — see [`LICENSE`](LICENSE).
