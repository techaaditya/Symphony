# Final submission checklist (design doc §21)

Status as of the end of the build. Items marked pending are the ones only the operator can
complete (recording a video, actually deploying to a real Alibaba Cloud account) — everything
buildable in code is done.

- [x] Public repo, visible OSS LICENSE at top of repo page — [`LICENSE`](../LICENSE) (MIT).
- [x] Full source, scenario data, setup instructions — see the [README](../README.md)'s Quickstart;
      `symphony/simulator/scenarios/wildfire_v3.json` is the only scenario, committed in full.
- [x] Separate Alibaba Cloud deployment proof recording, linked to specific code/config —
      [`infra/alibaba-cloud/proof/deployment-proof-recording.mp4`](../infra/alibaba-cloud/proof/deployment-proof-recording.mp4),
      screenshots and full details in
      [`infra/alibaba-cloud/deployment-proof-checklist.md`](../infra/alibaba-cloud/deployment-proof-checklist.md).
      Code file: [`symphony/config.py`](../symphony/config.py#L35) (DashScope base URL), used by
      [`symphony/llm/provider.py`](../symphony/llm/provider.py)'s `QwenProvider`.
- [x] Architecture diagram in README — [`docs/architecture.md`](architecture.md), linked from the
      README's Architecture section.
- [ ] ~3-minute public demo video — storyboard and voiceover ready
      ([`docs/demo-script.md`](demo-script.md)) and drivable end-to-end
      (`scripts/demo_run.py`); recording itself is operator-run.
- [x] Text description of features/functionality — the README's opening section plus the
      Parliament Protocol worked-example section.
- [x] Track: **Agent Society**.
- [x] Real, measured benchmark table in README (not placeholders) — README's "Benchmark: measured
      results" section, backed by
      [`symphony/benchmark/results/wildfire_v3_seed42_n20.json`](../symphony/benchmark/results/wildfire_v3_seed42_n20.json).
- [x] Worked conflict-resolution example in docs — the tick-10 (vote) and tick-15
      (escalation + veto) examples in the README, pulled from one real seeded run.
- [x] `responsible-ai.md` present as standalone file — [`responsible-ai.md`](../responsible-ai.md).
- [x] Self-audit (§19) completed — [`docs/self-audit.md`](self-audit.md), written after the real
      numbers were measured, including a documented methodology fix (the scenario budget) and two
      named limitations left as future work.

## What's left, concretely

1. Record the ~3-minute feature demo per `docs/demo-script.md`, using `scripts/demo_run.py` to
   drive the scenario at a narratable pace — run against the local `docker-compose.yml` stack, not
   the Alibaba Cloud instance (that instance can be released once the deployment proof is
   submitted; the feature demo doesn't depend on it).
2. Submit the feature demo video, the deployment-proof recording (already committed at
   `infra/alibaba-cloud/proof/`), and the code-file link alongside this repo on the hackathon
   submission form.
3. Release the ECS instance (`i-t4niew2qfik209oghsav`) once the submission is in, so it stops
   billing against the hackathon voucher.
