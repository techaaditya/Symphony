# Symphony — a multi-agent society for crisis response

**Global AI Hackathon Series with Qwen Cloud · Track 3: Agent Society**

A wildfire spreads across two districts. Helicopters, medic teams, search-and-rescue crews, comms
towers and a fixed budget all run short at the worst possible moment. One generalist coordinator,
trying to hold the whole picture in its head, is exactly the wrong tool for that — it has no way to
weigh a trapped-persons rescue against a structure fire against a blown budget, and no record of
why it chose what it chose.

Symphony replaces that lone decision-maker with a **society of five specialist agents** —
Logistics, Medical, Comms, Finance, and Search & Rescue — who argue it out. Each proposes what its
own domain needs; when two of them reach for the same helicopter, a structured **Parliament
Protocol** (propose → debate → vote → escalate → commit) settles it, and every step is written down.

The one rule underneath everything:

> **Agents propose. Deterministic code adjudicates.**

An LLM writes each proposal, each rebuttal, each persuasiveness score. But *who wins a conflict* is
never left to a model — conflict detection, the weighted vote, the Finance veto, and the commit are
all plain, unit-tested Python. The society is creative where creativity helps and mechanical where
trust matters.

---

## How this maps to Track 3

Track 3 asks for three things. Here is exactly where each one lives:

| Track 3 asks for… | In Symphony |
| --- | --- |
| **How agents decompose tasks and assign roles** | Five specialists, each owning one domain with its own action set and a fixed **expertise-weight table** (`symphony/agents/*.py`). A crisis event is decomposed by *which specialist it belongs to*; nobody acts outside their remit. |
| **How they resolve disagreements and execution conflicts** | The **Parliament Protocol** (`symphony/protocol/parliament.py`): bounded debate, an expertise-weighted vote, Coordinator escalation on a close call, and a Finance veto with a unanimous-override path — two genuinely different resolution mechanisms, both visible in one real run. |
| **A measurable efficiency gain over single-agent baselines** | A committed 20-trial benchmark. The society is the **only** mode that finishes the scenario **within budget — 20/20 trials vs 0/20** for the baseline, which "succeeds" only by overspending money it doesn't have. See [Benchmark](#the-benchmark-what-actually-improves). |

---

## What it does, in one run

`symphony sim --scenario wildfire_v3 --seed 42` plays out 20 time-steps. Each step:

1. The simulator injects the next scripted event — a fire spreads, casualties are reported, a comms
   tower fails, a rescue window opens.
2. All five specialists read the shared **blackboard** (the current world state) and each returns one
   proposal from its own expertise.
3. If two proposals claim the same scarce resource, that's a **conflict**, and the Parliament
   Protocol runs: up to three rounds of rebuttal, an expertise-weighted vote, escalation to the
   Coordinator if the vote is close, and a Finance veto if the budget can't absorb the spend.
4. The outcome commits to the blackboard and appends to an immutable **ledger**; every conflict is
   also written to a **conflict graph** you can explore.

Nothing above is hand-waved in a slide. It runs, it's seeded, it's identical every time, and the
dashboard lets you watch it happen.

---

## The Parliament Protocol, from a real seed-42 run

State machine: `OPEN_ROUND → CONFLICT_CHECK → DEBATE → VOTE → ESCALATE → COMMIT`. Every number below
is real output from `symphony sim --scenario wildfire_v3 --seed 42` — nothing is illustrative.

**The weighted vote.** For a conflict over resource `R`, each contending side `s` scores:

```text
side_score(s) = Σ  (neutral voter v's expertise weight on R) × (v's average persuasiveness score of s's rebuttal)
                v
```

Expertise weight is 1.0 in an agent's specialty, 0.8–0.9 in an adjacent domain, and 0.5 for a
resource outside its lane (`symphony/agents/*.py`). Persuasiveness is averaged over every bounded
debate round (`MAX_DEBATE_ROUNDS = 3`). A side wins outright only if it beats the runner-up by
`MAJORITY_THRESHOLD = 1.2×`; otherwise the conflict escalates to the Coordinator.

### Tick 10 — a clean vote, settled without escalation

Three agents want the one remaining helicopter:

| Agent | Rationale | Confidence |
| --- | --- | --- |
| Logistics | "Zone zone-1 fire intensity is 0.58; a helicopter water drop is the fastest way to slow the spread." | 0.93 |
| Medical | "8 critical casualties in zone zone-2; a confirmed casualty's time-criticality outweighs a hypothetical future one." | 0.72 |
| SAR | "2 trapped in zone zone-1 with only 3 ticks left in the rescue window; ground SAR teams are too slow." | 0.77 |

Comms and Finance are neutral here (both weigh "helicopter" at the 0.5 baseline). Averaging their
persuasiveness scores across all three rounds gives exactly what the ledger recorded:

| Side | Comms avg | Finance avg | `side_score` |
| --- | --- | --- | --- |
| Logistics | 0.57 | 0.70 | 0.5·0.57 + 0.5·0.70 = **0.635** |
| Medical | 0.75 | 0.85 | 0.5·0.75 + 0.5·0.85 = **0.800** |
| SAR | 0.39 | 0.76 | 0.5·0.39 + 0.5·0.76 = **0.575** |

Medical wins outright — 0.800 > 0.635 × 1.2 = 0.762 — and is committed. No escalation needed.

### Tick 13 — escalation and veto in the same round

Budget is down to **$36,500**. Logistics (fighting the fire) and SAR (a rescue window with *zero*
ticks left) both want the helicopter:

- The vote is **1.096 (Logistics) vs 1.313 (SAR)** — SAR leads, but 1.313 is *not* greater than
  1.096 × 1.2 = 1.315. It misses the majority threshold by two thousandths, so it **escalates**.
- The **Coordinator** reads the actual debate transcript and rules for SAR, quoting the rebuttal it
  found most grounded.
- But Finance had already raised a veto this same tick:

  > "Remaining budget $36,500 is below the $45,000 ceiling needed to safely absorb another
  > helicopter deployment this tick." — Finance, `veto_target: "helicopter"`

The veto is applied *after* the ruling. Overriding it would take a unanimous, high-confidence
proposal from all four non-Finance agents (`OVERRIDE_CONFIDENCE_THRESHOLD` in `parliament.py`) —
that didn't happen, so **SAR's won ruling is dropped** (`reason: "finance_veto"`). Only Medical and
Comms commit.

This is the point of the whole design: **a vote can be won and still not executed.** One mechanism
(the weighted vote + escalation) decides who has the strongest case; a second, independent one (the
veto) decides whether the society can afford to act on it at all.

---

## The benchmark: what actually improves

`symphony benchmark --scenario wildfire_v3 --seed 42 --n 20` — the five-agent society against a
single generalist agent, identical scenario and seeds, 20 trials each. The baseline is a fair one:
it sees the same blackboard and calls the same model, just once per tick instead of five times, and
commits through the same code. Raw numbers committed at
[`symphony/benchmark/results/wildfire_v3_seed42_n20.json`](symphony/benchmark/results/wildfire_v3_seed42_n20.json).

| Metric | Single-agent | Five-agent society |
| --- | --- | --- |
| **Finishes within budget** | **0 / 20 trials** (ends ≈ **−$35,000**) | **20 / 20 trials** (ends ≈ **+$36,500**) |
| Objectives met | 100.0% | 54.5% |
| Resource waste | 0.0% | 0.0% |
| Time to allocate | 0.006s | 0.078s |
| Token cost | 9,399 | 252,383 |

**Read this the honest way.** The single agent "meets 100% of objectives" — but only by spending
**$35,000 it does not have**, in every single trial. The simulator lets the budget go negative;
the real world does not. A plan that grounds your aircraft and bounces your payroll hasn't met its
objectives, it has failed expensively. The society meets fewer objectives (54.5%) because Finance
starts vetoing helicopter spend once the budget crosses its safety ceiling — and it is the **only**
configuration whose plan is actually executable, finishing solvent with a reserve in all 20 trials.

That is the measurable efficiency gain a governed society buys you: **feasibility under a hard
constraint.** Reproduce the budget number yourself with
[`scripts/budget_adherence.py`](scripts/budget_adherence.py):

```text
mode             mean final budget    trials within budget
single-agent               -35,000                 0 / 20
society                     36,500                20 / 20
```

The extra cost is real too, and stated plainly: the society spends ~27× the tokens (five proposals
plus up to three debate rounds per conflict, versus one call per tick). Whether that trade is worth
it depends on how much a blown budget costs you in the real scenario — which is a decision the
society makes *auditable* rather than invisible.

> The scenario's 180,000 starting budget was chosen so the budget constraint actually *binds* — an
> earlier value left the Finance veto dormant across every seed, which under-tested the exact
> mechanism the system exists to demonstrate. It's a deliberate benchmark-design choice to make the
> constraint real, not a number picked to flatter the result (see [Honest limitations](#honest-limitations)).

---

## Runs offline, at zero cost, by default

Every external dependency sits behind a small interface with a local, zero-config default and an
opt-in live backend selected by an environment variable (`symphony/config.py`):

| Concern | Default (no setup) | Live backend (opt-in) |
| --- | --- | --- |
| LLM | Deterministic `MockProvider` | **Qwen** via DashScope — `SYMPHONY_LLM=qwen` |
| Event bus | In-memory | **ApsaraMQ for Kafka** — `SYMPHONY_BUS=kafka` |
| Blackboard | In-memory | **Alibaba Tablestore** — `SYMPHONY_BLACKBOARD=tablestore` |
| Conflict graph | Local JSON file | **Neo4j** — `NEO4J_URI=…` |

The entire system — simulator, agents, protocol, ledger, benchmark, dashboard, and all 87 tests —
runs with **no API keys and no token cost** on the mock LLM. The mock isn't a toy: it's engineered
to manufacture real conflicts and a reachable Finance veto, so every branch of the protocol is
exercised offline before a single token is spent. Flip one env var and the *exact same code path*
runs against live Qwen and managed Alibaba Cloud services.

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

- **Dashboard** → <http://localhost:3000> — live map, command matrix, ledger replay, conflict-graph
  explorer, benchmark chart
- **API docs** → <http://localhost:8000/docs>
- **Neo4j browser** → <http://localhost:7474> (`neo4j` / `symphony123`)

`make down` stops it; `make clean` also wipes the Neo4j volume. See the [`Makefile`](Makefile) for
`logs`, `build`, `test`, `bench`.

### A live Qwen run (real API calls)

```bash
SYMPHONY_LLM=qwen DASHSCOPE_API_KEY=… symphony sim --scenario wildfire_v3 --seed 42
```

---

## The five specialists (task decomposition)

Each agent owns a domain, a fixed action set, and an expertise-weight table that determines how much
its vote counts on a given resource. This *is* the role assignment — a crisis event is handled by
whoever it belongs to.

| Agent | Owns | Weighs heaviest on | Can do |
| --- | --- | --- | --- |
| **Logistics** | Vehicles, air support routing | helicopter (1.0) | route helicopters/ground vehicles |
| **Medical** | Casualties, triage | medic team (1.0), helicopter (0.8) | deploy medics, request air transport, retriage |
| **Search & Rescue** | Trapped persons | sar team (1.0), helicopter (0.8) | deploy SAR teams, request air transport |
| **Comms** | Tower network | comms tower (1.0) | repair / reprioritize towers |
| **Finance** | The budget | budget (1.0) | flag budget risk, **veto** an unaffordable spend |
| **Coordinator** | Deadlocks only | — | rule on an escalated conflict, citing the transcript |

The Coordinator never proposes actions — it only breaks ties the society couldn't, and only by
pointing at what was actually said in the debate.

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

The design principle shows up structurally: the LLM (Mock or Qwen) touches only the *propose*,
*debate*, and *score* boxes. Every arrow that decides an outcome is deterministic Python.

---

## Beyond wildfires

The wildfire is a vehicle. What's actually general is the shape: **several specialists with
different stakes, contending for a shared pool of scarce, indivisible resources, needing an
auditable process instead of one opaque decision-maker.** That's supply-chain allocation during a
shortage, multi-team incident response, cross-department budget arbitration. The Parliament Protocol
and the Finance-style veto are domain-agnostic; only the agents' prompts and `wildfire_v3.json` are
wildfire-specific. Swapping the scenario file and the five prompts retargets the whole society.

---

## Repository layout

```text
symphony/
├── symphony/                     # Python backend
│   ├── config.py                 # env-driven adapter selection
│   ├── simulator/                # seeded world + wildfire_v3 scenario
│   ├── agents/                   # 5 specialists + Coordinator + prompts
│   ├── protocol/                 # Parliament Protocol, veto, commit, conflict graph
│   ├── llm/                      # MockProvider + QwenProvider (DashScope)
│   ├── blackboard/  bus/  ledger/
│   ├── benchmark/                # harness + committed results
│   └── api/                      # FastAPI server + SSE stream
├── dashboard/                    # Next.js: map, command matrix, ledger, conflicts, benchmark
├── infra/alibaba-cloud/          # Terraform + bootstrap/health scripts for the real deploy
├── scripts/                      # demo driver, budget-adherence measurement
├── docker-compose.yml            # local Neo4j + Redpanda + api + dashboard
└── tests/                        # 87 tests, mock LLM, zero network
```

---

## Proof of Alibaba Cloud deployment

The backend was deployed and run on an Alibaba Cloud ECS instance using live Qwen (DashScope). The
recording and Workbench screenshots are provided with the hackathon submission. The code that talks
to Alibaba Cloud is [`symphony/llm/provider.py`](symphony/llm/provider.py) — `QwenProvider` calls
DashScope's OpenAI-compatible endpoint, selected by `symphony/config.py`.

---

## Honest limitations

Stated up front, because a benchmark that only flatters you is a bug report:

- **The scenario budget was tuned to make the constraint bind.** As above, the 180,000 figure was
  chosen deliberately so the Finance veto actually fires and the governance difference becomes
  measurable. It makes the constraint real; it isn't a number reverse-engineered to make the society
  win. The society wins *because* it respects a real constraint the baseline ignores.
- **`resource_waste_pct` reads 0.0% for both modes on this scenario.** The waste metric only triggers
  when an agent serves an already-resolved objective, which the agents never do here. The logic is
  unit-tested with a synthetic case (`tests/test_benchmark.py`), but it has not gone non-zero in a
  real run on this scenario.
- **Rescue timing is not yet scored.** A trapped-persons objective rescued one tick after its window
  closes currently counts the same as one rescued on time. The window is modeled and shown in agent
  rationales, but `objectives_met_pct` only checks whether the rescue eventually happened. Fixing it
  is documented future work, not silently shipped as if the number already accounts for it.

Model choices, data provenance (all scenario data is synthetic — no real people, places, or
incidents), and an explicit statement of what this system is *not* are in
[`responsible-ai.md`](responsible-ai.md).

## License

MIT — see [`LICENSE`](LICENSE).
