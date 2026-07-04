# Deployment-proof checklist

The submission checklist (design doc §21) requires a **separate Alibaba
Cloud deployment proof recording, linked to specific code/config** — distinct
from the ~3-minute feature demo video. This is that recording's checklist.

Record this *after* completing [`DEPLOY_RUNBOOK.md`](DEPLOY_RUNBOOK.md)
through step 6, on the real deployed instance — not localhost, not
docker-compose.yml's local stack.

## What to show, in order

- [ ] **The Terraform apply output** — scroll to the `Apply complete!` line
      showing resources actually created (ECS, Tablestore, ApsaraMQ for
      Kafka, RAM, networking), or the saved terminal output if recording
      live apply isn't practical.
- [ ] **The Alibaba Cloud console**, side by side with the code that
      provisioned each resource:
  - [ ] ECS instance running → `infra/alibaba-cloud/terraform/ecs_neo4j.tf`
  - [ ] Tablestore instance + `symphony_blackboard` table →
        `infra/alibaba-cloud/terraform/tablestore.tf` and
        `symphony/blackboard/tablestore_store.py`
  - [ ] ApsaraMQ for Kafka instance + `symphony-events` topic →
        `infra/alibaba-cloud/terraform/kafka.tf` and
        `symphony/bus/kafka_bus.py`
- [ ] **The Neo4j browser** (`http://<host>:7474`) showing real
      `CONFLICTED_WITH` edges from the seeded run — run a Cypher query on
      camera, e.g. `MATCH (a:Agent)-[:PROPOSED]->(p:Proposal)-[r:CONFLICTED_WITH]->(p2) RETURN a,p,r,p2 LIMIT 25`.
- [ ] **The API docs** (`http://<host>:8000/docs`) — expand one endpoint to
      show it's the real deployed FastAPI instance, not localhost.
- [ ] **The dashboard** (`http://<host>:3000`) — the URL bar visibly showing
      the ECS public IP, not `localhost:3000`, while a live run animates the
      agent graph and disaster map.
- [ ] **`.env.production`'s adapter settings** (redact the actual secret
      values, show the variable *names* and that `SYMPHONY_BLACKBOARD=tablestore`
      / `SYMPHONY_BUS=kafka` / `NEO4J_URI=bolt://...` are set to the live
      backends, not the local defaults) — proves this run used the real
      adapters, not the zero-config in-memory ones.

## What NOT to show

- Any real AccessKey ID/secret, RAM access key, Neo4j password, or
  DashScope API key on screen — redact or blur these; regenerate them after
  recording if any were shown by mistake.

## After recording

- [ ] Upload/link the recording per the hackathon submission form.
- [ ] Run `infra/alibaba-cloud/DEPLOY_RUNBOOK.md`'s teardown step (`terraform
      destroy`) so the metered Tablestore/Kafka instances stop billing.
- [ ] Note the recording's URL in the main submission README alongside the
      ~3-minute feature demo video.
