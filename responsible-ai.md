# Responsible AI — Symphony

## Who This Tool Is For

Symphony is a hackathon research/demo prototype exploring multi-agent negotiation patterns for
scarce-resource coordination, using a simulated disaster scenario as a concrete, demoable test bed.
It is explicitly **NOT** a real emergency-response dispatch or decision-support tool.

## Model Choices & Rationale

- A fast/economical Qwen tier powers the five specialist agents (high call volume, moderate
  individual complexity — see the cost rationale in the main README).
- A top-tier Qwen reasoning model powers the Coordinator, invoked only on genuine deadlock, where
  higher-quality single-shot reasoning matters most.
- Conflict detection, vote tallying, veto enforcement, and commit logic are all deterministic
  Python — never delegated to a generative model ("agents propose, deterministic code
  adjudicates").
- By default the system runs on a deterministic, offline `MockProvider` so the protocol logic,
  tests, and demos can be developed and verified at zero token cost before any live model call is
  made.

## Data Sources

All scenario data (zones, events, casualties, resource pools) is synthetically generated for this
simulation. No real disaster, casualty, or dispatch data of any kind is used, referenced, or
approximated.

## Bias & Limitation Considerations

- Each agent's "utility function" is a deliberately simplified proxy for a real specialist's
  priorities and does not capture the full complexity of real emergency-response decision-making,
  resource constraints, jurisdictional authority, or legal/ethical obligations that real
  responders operate under.
- The benchmark's single-agent baseline is one reasonable design for a baseline, not the only
  possible one — a differently-prompted or differently-scaffolded single-agent baseline could
  perform differently, and the reported efficiency gain should be read as evidence for this
  specific comparison, not a universal claim about multi-agent systems outperforming single agents
  in general.
- The disaster simulator's event model (fire spread, casualty accumulation, etc.) is a simplified
  deterministic/seeded-random abstraction for demo purposes, not a validated disaster-modeling
  tool.

## Failure Cases & Mitigations

| Failure Case | Mitigation |
|---|---|
| An agent's LLM call fails mid-round | Agent abstains for that round rather than crashing the tick |
| Vote produces a near-tie | Escalates to Coordinator rather than resolving by an arbitrary default |
| Finance veto disputed | Requires unanimous override from the other four agents, logged explicitly |
| Benchmark run produces an unexpectedly clean/perfect result | Treated as a signal to re-check methodology for an inadvertent baseline handicap before reporting, not as a result to celebrate uncritically |

## What This System Is NOT

| Not This | Notes |
|---|---|
| A real emergency-dispatch or decision-support tool | Simulation only, synthetic data only |
| A validated disaster model | Simplified, deterministic/seeded abstraction |
| A general proof that multi-agent systems beat single agents | Evidence specific to this benchmark design, stated as such |
| Production software | Hackathon prototype |

## Transparency Commitments

- Every deliberation round, including abstentions and vetoes, is logged to the ledger and
  explorable via the Conflict Graph Explorer — nothing is a black box.
- Benchmark numbers reported in the README are real, measured results from the actual harness in
  `symphony/benchmark/run_benchmark.py`, not illustrative placeholders.

## Disclaimer

This is a hackathon prototype exploring multi-agent coordination patterns using a simulated
disaster scenario. It must not be used, referenced, or adapted for real emergency response,
dispatch, or resource-allocation decisions without extensive independent validation,
domain-expert review, and regulatory consideration far beyond the scope of this project.
