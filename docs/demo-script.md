# Demo video script (~3 minutes)

Plain-language voiceover with on-screen directions. Record the dashboard views in this order:
**Live → Ledger → Conflicts → Benchmark**. Everything shown is a real seeded run
(`wildfire_v3`, seed 42) — no mockups.

## Before you record

```bash
make up                      # local stack: neo4j, redpanda, api, dashboard
python scripts/demo_run.py   # drives the scenario at a narratable pace
```

Open <http://localhost:3000/live> in the browser *before* you start `demo_run.py`, so the map and
command matrix are on screen when the ticks begin.

---

## The script

### 0:00 – 0:20 · The problem

*(On screen: the Live view, disaster map with two zones, fire just starting.)*

> "A wildfire is spreading across two districts. There are more emergencies than there are
> helicopters, medics, and money to go around. Normally you'd hand this to one AI assistant and hope
> it makes good calls. But one assistant can't be an expert in everything at once — and it can't show
> you *why* it chose what it chose. So we didn't build one assistant. We built five, and gave them a
> way to argue."

### 0:20 – 0:45 · Meet the society

*(On screen: the Command Matrix — five department cards: Logistics, Medical, Comms, Finance, Search
& Rescue. Click "Start scenario." The map begins updating.)*

> "Meet the team. Logistics moves vehicles and aircraft. Medical handles casualties. Search and
> Rescue reaches trapped people. Comms keeps the towers up. And Finance guards the budget. Each one
> is a specialist — it only proposes actions in its own lane. Watch what happens when the fire
> forces them to compete."

### 0:45 – 1:25 · A conflict, resolved in the open

*(On screen: switch to Ledger, scrub to tick 10.)*

> "Here at step ten, there's exactly one helicopter left, and three agents want it. Logistics wants
> it to fight the fire. Medical wants it for eight critical casualties. Search and Rescue wants it
> for people trapped with minutes left. That's a real three-way conflict."

*(Point at the debate transcript and the vote.)*

> "So the society debates. The two agents with no stake — Comms and Finance — score how convincing
> each side is. Those scores become a weighted vote, and Medical's case wins outright. No human
> stepped in. The decision, and the reasoning behind it, is written down."

### 1:25 – 2:05 · A vote can be won — and still refused

*(On screen: scrub to tick 13.)*

> "A few steps later, it gets more interesting. The budget is down to thirty-six thousand dollars.
> Logistics and Search and Rescue tie so closely the society can't settle it, so it escalates to a
> Coordinator, who reads the transcript and rules for Search and Rescue."

*(Point at the veto line.)*

> "But Finance had already raised a flag: there isn't enough money left to safely put another
> helicopter in the air. So the veto overrides the ruling. Search and Rescue *won the vote* — and
> still doesn't get the helicopter, because the society can't afford it. That's the whole idea: being
> right isn't the same as being affordable, and the system keeps those two things separate."

### 2:05 – 2:25 · Every disagreement, on the record

*(On screen: switch to Conflicts, focus agent = Logistics.)*

> "And none of this is a black box. Every clash across the whole run is here as a graph — every time
> Logistics fought over that helicopter, who it was against, and how it ended. A supervisor can audit
> the entire crisis after the fact."

### 2:25 – 2:50 · Does the society actually do better?

*(On screen: switch to Benchmark, run the comparison.)*

> "Now the honest question — is five agents actually better than one? We ran both, twenty times.
> The single agent looks perfect: it completes every objective. But it only does that by spending
> thirty-five thousand dollars it doesn't have — every single trial. In the real world, that's
> grounded aircraft and unpaid crews. The society completes fewer objectives, but it finishes inside
> the budget every single time. It's the only one whose plan you could actually carry out."

### 2:50 – 3:00 · Close

*(On screen: architecture diagram, or back to the map.)*

> "Five specialists, one auditable process, running on Alibaba Cloud with Qwen. One rule underneath
> all of it: the agents propose, and deterministic code decides. That's Symphony."

---

## After recording

Record the separate Alibaba Cloud deployment-proof clip per
[`../infra/alibaba-cloud/deployment-proof-checklist.md`](../infra/alibaba-cloud/deployment-proof-checklist.md).
It is **not** part of this ~3-minute demo.
