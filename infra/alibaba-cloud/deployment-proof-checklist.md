# Deployment-proof checklist

The submission checklist (design doc §21) requires a **separate Alibaba Cloud deployment proof
recording, linked to specific code/config** — distinct from the ~3-minute feature demo video.

## What was actually done for this submission

**Scope actually deployed: the minimal proof, not the full Terraform stack.** The Terraform in
`infra/alibaba-cloud/terraform/` (ECS + Tablestore + ApsaraMQ for Kafka + RAM) is real,
validated-for-real infrastructure-as-code (`terraform validate`/`plan` against real provider
schemas caught a genuine Tablestore instance-name-length bug), but running it end to end needs an
Alibaba Cloud AccessKey and a bound payment method configured well before a deadline. What was
actually deployed for the required proof, under real time pressure, was simpler and still fully
genuine:

- **One ECS instance**, created directly via the Alibaba Cloud console (not `terraform apply`):
  `i-t4niew2qfik209oghsav`, 2 vCPU / 4 GiB, Singapore region, Ubuntu 22.04.
- **The Symphony API** (`symphony/api/app.py`), running as a systemd service on that instance —
  not inside Docker, for speed — configured with `SYMPHONY_LLM=qwen` and a real DashScope API key.
- **Bus, blackboard and conflict graph left on their zero-config local defaults** for this proof
  (in-memory / JSON file) — only the LLM adapter is live. The pluggable-adapter design means this
  is a legitimate partial-live configuration, not a fake one: `symphony/config.py`'s `is_live`
  check and `get_provider()` genuinely select the live `QwenProvider` based on real env vars on
  the real instance, verified by reading the actual running process's environment
  (`/proc/<pid>/environ`), not just a config file.

## Evidence, committed in this folder

- [`ecs-workbench-running.png`](proof/ecs-workbench-running.png) — Alibaba Cloud ECS Workbench
  showing `i-t4niew2qfik209oghsav` **Running**, Singapore, public IP `47.84.55.137`.
- [`api-docs-live.png`](proof/api-docs-live.png) — the live Symphony API's `/docs` page, served
  from that public IP.
- [`deployment-proof-recording.mp4`](proof/deployment-proof-recording.mp4) — the short recording:
  Workbench showing the running instance, then the live API responding to a real request.

**Code file proving Qwen Cloud API usage** (per the hackathon's exact ask — a code file with the
base URL visible): [`symphony/config.py`](../../symphony/config.py#L35) (the literal
`https://dashscope-intl.aliyuncs.com/compatible-mode/v1` — or the workspace-specific MaaS host,
matching whichever your account's Model Studio console shows), used by
[`symphony/llm/provider.py`](../../symphony/llm/provider.py)'s `QwenProvider` class to make real
`chat.completions.create()` calls.

**Independent verification this was real, not mock**, done live during the deploy session:

- The running process's actual environment (`/proc/<pid>/environ`) showed `SYMPHONY_LLM=qwen` and
  the real DashScope key/endpoint — not just a config file that could be stale.
- A real `POST /sim/tick` call took **~3 seconds** round-trip — consistent with a real DashScope
  API call; the deterministic `MockProvider` returns in milliseconds.
- `journalctl` on the instance showed the actual external requests, from an outside IP, hitting
  the service.

## What was intentionally NOT shown / not done

- No AccessKey ID/secret, RAM access key, Neo4j password, or the DashScope API key appear on
  screen in the recording or screenshots.
- Tablestore and ApsaraMQ for Kafka were **not** provisioned for this proof (cost/time tradeoff,
  documented honestly above) — the Terraform for them exists and is validated, but wasn't applied.

## After recording (do this next)

- [x] Evidence committed to this repo (this folder).
- [x] Code file link identified (see above).
- [ ] Stop or release the ECS instance (`i-t4niew2qfik209oghsav`) once the submission is in, so it
      stops billing against the hackathon voucher.
- [ ] Paste the recording + screenshot + code file link into the hackathon submission form.
