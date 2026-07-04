# Demo video script (~3:00)

Storyboard and voiceover, adapted from the design doc §18 with the placeholders filled in by real
output from `scripts/demo_run.py --scenario wildfire_v3 --seed 42` against the local
`docker-compose.yml` stack. Record the dashboard's **Live**, **Ledger**, **Conflicts**, and
**Benchmark** views in that order — the same order the voiceover below expects.

## Before recording

```bash
make up                      # local stack: neo4j, redpanda, api, dashboard
python scripts/demo_run.py   # drives the actual scenario used below, at demo pace
```

Open `http://localhost:3000/live` in the browser *before* running `demo_run.py`, so the map and
agent graph are already on screen when ticks start arriving.

## Storyboard

**(0:00–0:20)** *(show the disaster map, both zones visible, fire intensity still low)*

> "Crisis response needs specialists negotiating in real time — not one generalist guessing
> alone. Here's a wildfire unfolding across two zones."

**(0:20–0:50)** *(agent graph lighting up as ticks 1-3 commit without conflict)*

> "Five agents — Logistics, Medical, Comms, Finance, Search and Rescue — each with their own
> objective, start proposing actions the moment the fire spreads."

**(0:50–1:35)** *(switch to Ledger view, scrub to tick 10)*

> "Watch this: at tick 10, casualties just came in at zone two, critical severity. Medical wants
> the helicopter. Logistics wants it to fight the fire instead — and Search and Rescue wants it
> for a trapped-persons window that's about to close. That's a real three-way conflict. Watch the
> debate resolve it: Medical's rebuttal scores highest with the two neutral agents, wins the
> weighted vote outright, no escalation needed."

**(1:35–2:05)** *(stay in Ledger view, scrub to tick 15)*

> "Five ticks later, it's not so clean. Logistics and Medical are close enough that it escalates
> to the Coordinator, who has to actually cite the debate transcript in its ruling, not just
> guess — and rules for Medical. But watch: Finance already flagged that the budget crossed its
> safety ceiling this same tick. The veto overrides the Coordinator's own ruling. That's the
> second, genuinely distinct conflict-resolution mechanism — a vote can be won and still not
> committed."

**(2:05–2:30)** *(switch to Conflicts view, focus agent = logistics)*

> "Every conflict this entire scenario is explorable as a graph — here's every time Logistics
> clashed over the helicopter, across the full run, tick by tick."

**(2:30–2:55)** *(switch to Benchmark view, run the n=20 comparison live or show the pre-run chart)*

> "And here's the actual measured result: twenty trials each, five-agent society against a single
> generalist agent, identical scenario and seeds. The society doesn't just win — it resolves
> two-thirds of the objectives because Finance's veto is actually protecting the budget, something
> the single generalist never does at all. That costs completed objectives, and it costs about
> twenty-six times the tokens. That's the honest tradeoff, not a cherry-picked one."

**(2:55–3:00)** *(architecture diagram from `docs/architecture.md`, close)*

> "Deployed on Alibaba Cloud. One rule underneath all of it: agents propose, deterministic code
> adjudicates."

## After recording

Record the separate Alibaba Cloud deployment-proof video per
[`infra/alibaba-cloud/deployment-proof-checklist.md`](../infra/alibaba-cloud/deployment-proof-checklist.md)
— it is **not** part of this ~3-minute feature demo.
