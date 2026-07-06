# Symphony - a multi-agent society for crisis response

**Global AI Hackathon Series with Qwen Cloud · Track 3: Agent Society**

A wildfire spreads across two districts. Helicopters, medic teams, rescue crews, comms towers and a
fixed budget all run short at the worst possible moment. One generalist coordinator holding the
whole picture in its head is the wrong tool for that - it can't weigh a rescue against a fire
against a blown budget, and it leaves no record of why it chose what it chose.

Symphony replaces that lone decision-maker with a **society of five specialist agents** - Logistics,
Medical, Comms, Finance, and Search & Rescue - who argue it out. Each proposes what its own domain
needs; when two reach for the same helicopter, a structured **Parliament Protocol** (propose →
debate → vote → escalate → commit) settles it, and every step is written down.

> **Agents propose. Deterministic code adjudicates.**

An LLM writes each proposal, rebuttal, and persuasiveness score. But *who wins a conflict* is never
left to a model - conflict detection, the weighted vote, the Finance veto, and the commit are all
plain, unit-tested Python. Same seed, same run, every time.

---

## How this maps to Track 3

| Track 3 asks for… | In Symphony |
| --- | --- |
| **How agents decompose tasks and assign roles** | Five specialists, each with its own action set and a fixed **expertise-weight table** (`symphony/agents/*.py`). A crisis event is handled by whoever it belongs to; nobody acts outside their remit. |
| **How they resolve disagreements and execution conflicts** | The **Parliament Protocol** (`symphony/protocol/parliament.py`): bounded debate, an expertise-weighted vote, Coordinator escalation on a close call, and a Finance veto with a unanimous-override path - two genuinely different resolution mechanisms, both below. |
| **A measurable efficiency gain over single-agent baselines** | A committed 20-trial benchmark. The society is the **only** mode that finishes within budget - 20/20 trials vs 0/20 for the baseline, which "succeeds" only by overspending money it doesn't have. See [The benchmark](#the-benchmark-what-actually-improves). |

---

## The Parliament Protocol, from a real seed-42 run

State machine: `OPEN_ROUND → CONFLICT_CHECK → DEBATE → VOTE → ESCALATE → COMMIT`. For a conflict over
resource `R`, each contending side `s` scores:

```text
side_score(s) = Σ  (neutral voter's expertise weight on R) × (voter's avg. persuasiveness score of s's rebuttal)
```

A side wins outright only if it beats the runner-up by `MAJORITY_THRESHOLD = 1.2×`; otherwise the
conflict escalates to the Coordinator. Every number below is real output, not illustrative.

**Tick 10 - a clean vote.** Logistics, Medical and SAR all want the one remaining helicopter.
Comms and Finance are neutral, so their averaged persuasiveness scores decide it:

| Side | `side_score` |
| --- | --- |
| Logistics | 0.635 |
| **Medical** | **0.800** |
| SAR | 0.575 |

Medical wins outright (0.800 > 0.635 × 1.2) and commits. No escalation needed.

**Tick 13 - escalation and veto in the same round.** Budget is down to $36,500. Logistics and SAR
tie too closely to settle (1.096 vs 1.313 - just short of the 1.2× threshold), so it escalates. The
Coordinator reads the actual debate transcript and rules for SAR. But Finance had already vetoed:

> "Remaining budget $36,500 is below the $45,000 ceiling needed to safely absorb another helicopter
> deployment this tick." - Finance

The veto applies *after* the ruling, and overriding it needs a unanimous, high-confidence vote from
every other agent - that didn't happen, so **SAR's won ruling is dropped.** Only Medical and Comms
commit.

That's the design in one sentence: **a vote can be won and still not executed.** One mechanism picks
the strongest case; a second, independent one decides whether the society can afford to act on it.

---

## The benchmark: what actually improves

`symphony benchmark --scenario wildfire_v3 --seed 42 --n 20` - the five-agent society against a
single generalist agent, identical scenario and seeds, fair on both sides (same blackboard, same
model, same commit code - the baseline just decides alone). Raw numbers:
[`symphony/benchmark/results/wildfire_v3_seed42_n20.json`](symphony/benchmark/results/wildfire_v3_seed42_n20.json).

| Metric | Single-agent | Five-agent society |
| --- | --- | --- |
| **Finishes within budget** | **0 / 20 trials** (ends ≈ **-$35,000**) | **20 / 20 trials** (ends ≈ **+$36,500**) |
| Objectives met | 100.0% | 54.5% |
| Resource waste | 0.0% | 0.0% |
| Token cost | 9,399 | 252,383 |

The single agent "meets 100% of objectives" only by spending **$35,000 it does not have**, in every
trial. A plan that bounces payroll hasn't met its objectives, it has failed expensively. The society
meets fewer objectives because Finance vetoes spend it can't afford - and it's the **only**
configuration whose plan is actually executable, finishing solvent in all 20 trials. That's the
measurable efficiency gain: **feasibility under a hard constraint.** Reproduce it with
[`scripts/budget_adherence.py`](scripts/budget_adherence.py). The society costs ~27× the tokens
(five proposals plus debate, versus one call per tick) - a real tradeoff, stated plainly.

---

## Runs offline, at zero cost, by default

Every external dependency sits behind a small interface with a local default and an opt-in live
backend, selected by one environment variable (`symphony/config.py`):

| Concern | Default (no setup) | Live backend (opt-in) |
| --- | --- | --- |
| LLM | Deterministic `MockProvider` | **Qwen** via DashScope - `SYMPHONY_LLM=qwen` |
| Event bus | In-memory | **ApsaraMQ for Kafka** - `SYMPHONY_BUS=kafka` |
| Blackboard | In-memory | **Alibaba Tablestore** - `SYMPHONY_BLACKBOARD=tablestore` |
| Conflict graph | Local JSON file | **Neo4j** - `NEO4J_URI=…` |

The mock isn't a toy - it's engineered to manufacture real conflicts and a reachable Finance veto,
so every branch of the protocol runs offline before a single token is spent. Flip one env var and
the exact same code runs against live Qwen and managed Alibaba Cloud services.

---

## Quickstart

### Just the core (no Docker, zero cost)

```bash
pip install -e ".[dev]"
pytest -q                                       # 87 tests, mock LLM, no network

symphony sim --scenario wildfire_v3 --seed 42    # one seeded run, printed tick by tick
symphony benchmark --n 20                        # society vs single-agent, mean/SD
python scripts/budget_adherence.py               # the budget-feasibility comparison
```

### The full stack (dashboard + REST API + real Neo4j + real Kafka)

```bash
cp .env.example .env       # optional; still zero-cost by default
make up                    # builds & starts neo4j, redpanda, api, dashboard
make seed                  # drives one real scenario through the running stack
```

- **Dashboard** → <http://localhost:3000> - live map, command matrix, ledger replay, conflict-graph
  explorer, benchmark chart
- **API docs** → <http://localhost:8000/docs>
- **Neo4j browser** → <http://localhost:7474> (`neo4j` / `symphony123`)

### A live Qwen run

```bash
SYMPHONY_LLM=qwen DASHSCOPE_API_KEY=… symphony sim --scenario wildfire_v3 --seed 42
```

---

## The five specialists

| Agent | Owns | Weighs heaviest on | Can do |
| --- | --- | --- | --- |
| **Logistics** | Vehicles, air support | helicopter (1.0) | route helicopters/ground vehicles |
| **Medical** | Casualties, triage | medic team (1.0), helicopter (0.8) | deploy medics, request air transport |
| **Search & Rescue** | Trapped persons | sar team (1.0), helicopter (0.8) | deploy SAR teams, request air transport |
| **Comms** | Tower network | comms tower (1.0) | repair towers |
| **Finance** | The budget | budget (1.0) | flag budget risk, **veto** unaffordable spend |
| **Coordinator** | Deadlocks only | - | rule on an escalated conflict, citing the transcript |

The Coordinator never proposes actions - it only breaks ties, and only by pointing at what was
actually said in the debate.

---

## Architecture

```text
Simulator ──events──▶ Event bus (in-memory / ApsaraMQ-Kafka)
    │
    └──state──▶ Blackboard (in-memory / Tablestore) ──▶ Parliament Protocol
                                                          │  propose · debate · vote
                                                          │  escalate · veto · commit
                                                          ▼
                        Ledger (JSONL)  +  Conflict graph (JSON / Neo4j)
                                                          │
                     FastAPI (REST + SSE)  ──fetch──▶  Next.js dashboard
```

The LLM (Mock or Qwen) touches only the *propose*, *debate*, and *score* boxes. Every arrow that
decides an outcome is deterministic Python.

---

## Beyond wildfires

What generalizes is the shape: several specialists with different stakes, contending for a shared
pool of scarce, indivisible resources, needing an auditable process instead of one opaque
decision-maker. That's supply-chain allocation during a shortage, multi-team incident response,
cross-department budget arbitration. The Parliament Protocol and the Finance-style veto are
domain-agnostic; only the agents' prompts and `wildfire_v3.json` are wildfire-specific.

---

## Repository layout

```text
symphony/
├── symphony/            # Python backend: config, simulator, agents, protocol, llm, benchmark, api
├── dashboard/           # Next.js: map, command matrix, ledger, conflicts, benchmark
├── infra/alibaba-cloud/ # Terraform + bootstrap/health scripts for the real deploy
├── scripts/             # demo driver, budget-adherence measurement
├── docker-compose.yml   # local Neo4j + Redpanda + api + dashboard
└── tests/               # 87 tests, mock LLM, zero network
```

---

## Proof of Alibaba Cloud deployment

The backend was deployed and run on an Alibaba Cloud ECS instance using live Qwen (DashScope). The
code that talks to Alibaba Cloud is [`symphony/llm/provider.py`](symphony/llm/provider.py) -
`QwenProvider` calls DashScope's OpenAI-compatible endpoint, selected by `symphony/config.py`.

---

## Honest limitations

- **The scenario budget (180,000) was tuned deliberately** so the Finance veto actually fires and
  the governance difference becomes measurable - not a number picked to flatter the result. The
  society wins because it respects a real constraint the baseline ignores.
- **`resource_waste_pct` reads 0.0% for both modes on this scenario.** The metric only triggers when
  an agent serves an already-resolved objective, which never happens here; verified with a synthetic
  test case, but hasn't gone non-zero in a real run yet.
- **Rescue timing isn't scored.** A rescue one tick after its window closes counts the same as one on
  time - a modeled but unscored edge, left as documented future work.

Model choices, data provenance (all scenario data is synthetic), and what this system is *not* are
in [`responsible-ai.md`](responsible-ai.md).

## License

MIT - see [`LICENSE`](LICENSE).
