# Alibaba Cloud deploy runbook

Stands up the same stack `docker-compose.yml` runs locally (Phase 13), but
against real managed Alibaba Cloud services instead of local containers:
Tablestore for the blackboard, ApsaraMQ for Kafka for the event bus, and
Neo4j on ECS for the Conflict Graph Explorer. This is the operator-run half
of the project — I (the assistant) wrote and reviewed every file here, but
did not and could not run `terraform apply` myself (no credentials, no
Terraform CLI in my environment). Read every step before running it.

## 0. Prerequisites

- An Alibaba Cloud account with billing enabled and an AccessKey pair with
  permission to create ECS, VPC, Tablestore, ApsaraMQ for Kafka and RAM
  resources.
- [Terraform](https://developer.hashicorp.com/terraform/install) >= 1.5.
- An SSH key pair (`ssh-keygen -t ed25519` if you don't have one).
- `curl` locally, for `health-check.sh`.

## 1. Configure credentials and variables

```bash
export ALICLOUD_ACCESS_KEY="..."
export ALICLOUD_SECRET_KEY="..."
export TF_VAR_neo4j_password="pick-a-real-password"

cd infra/alibaba-cloud/terraform
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars: set ssh_public_key (contents of your .pub file) and
# allowed_ssh_cidr (your own IP/32 -- never 0.0.0.0/0).
```

## 2. Provision the infrastructure

```bash
terraform init
terraform plan    # review: 1 VPC, 1 vswitch, 1 security group + rules,
                   # 1 ECS instance, 1 Tablestore instance + table,
                   # 1 ApsaraMQ for Kafka instance + topic, 1 RAM user + key
terraform apply
```

ApsaraMQ for Kafka provisioning is genuinely slow — expect 10-30 minutes for
`apply` to finish. Once it's done:

```bash
terraform output
```

Note `neo4j_ecs_public_ip`. The Kafka instance's actual bootstrap-server
endpoint isn't a reliably-named Terraform attribute across provider versions
(see the comment on `alikafka_instance_id` in `outputs.tf`) — open the
Alibaba Cloud console, **Message Queue for Kafka → Instances → (this
instance) → Basic Information**, and copy its default endpoint.

## 3. Bootstrap Neo4j (doc §22's exact docker command)

```bash
cd ../scripts
NEO4J_HOST=$(terraform -chdir=../terraform output -raw neo4j_ecs_public_ip) \
NEO4J_PASSWORD="$TF_VAR_neo4j_password" \
./bootstrap-neo4j.sh
```

Confirm it's up: open `http://<neo4j_ecs_public_ip>:7474` in a browser and
log in with `neo4j` / your password.

## 4. Render `.env.production`

```bash
export NEO4J_PASSWORD="$TF_VAR_neo4j_password"
export KAFKA_BOOTSTRAP_SERVERS="<paste the endpoint from step 2>"
export DASHSCOPE_API_KEY="..."   # omit entirely to keep the deploy on the zero-cost MockProvider
./render-env.sh > ../../../.env.production
```

Open `.env.production` and sanity-check it against
[`.env.production.example`](../../.env.production.example) — it should have
every field filled in, no empty values.

## 5. Ship the app onto the ECS instance and start it

The ECS instance already has Docker (installed by Terraform's `user_data`).
Get the code onto it — simplest is a `git clone` of this public repo,
since the submission checklist requires the repo be public anyway:

```bash
NEO4J_HOST=$(terraform -chdir=../terraform output -raw neo4j_ecs_public_ip)
scp ../../../.env.production root@$NEO4J_HOST:/root/symphony/.env.production
ssh root@$NEO4J_HOST "cd /root && git clone <your-repo-url> symphony || (cd symphony && git pull)"
ssh root@$NEO4J_HOST "cd /root/symphony && docker compose -f docker-compose.prod.yml --env-file .env.production up --build -d"
```

(`--env-file` is required here — `env_file:` inside the compose file injects
variables into the *container*, but `docker compose`'s own `${...}`
interpolation, used for the dashboard's build arg, needs `--env-file` on the
command line.)

## 6. Verify

```bash
HOST=$(terraform -chdir=infra/alibaba-cloud/terraform output -raw neo4j_ecs_public_ip) \
infra/alibaba-cloud/scripts/health-check.sh
```

Then seed real data for the demo recording:

```bash
curl -X POST http://$HOST:8000/sim/start -H "Content-Type: application/json" \
  -d '{"scenario_id":"wildfire_v3","seed":42,"mode":"society"}'
# repeat POST /sim/tick with the returned sim_id until "finished": true,
# or just open http://$HOST:3000/live and click "Start scenario".
```

Now `http://$HOST:7474` (Neo4j browser), `http://$HOST:8000/docs` (API),
and `http://$HOST:3000` (dashboard) all reflect a real run against real
managed services. See [`deployment-proof-checklist.md`](deployment-proof-checklist.md)
for what to capture.

## 7. Tear down

Stop paying for this the moment you have your recording:

```bash
ssh root@$HOST "cd /root/symphony && docker compose -f docker-compose.prod.yml down"
cd infra/alibaba-cloud/terraform
terraform destroy
```

`terraform destroy` removes the ECS instance, Tablestore instance, ApsaraMQ
for Kafka instance, RAM user/key, and networking — the Tablestore/Kafka
instances are the ones actually billed by the hour, not just by usage, so
don't leave them up longer than needed.
