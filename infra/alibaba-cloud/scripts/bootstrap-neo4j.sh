#!/bin/bash
# Runs the design doc's exact Neo4j docker command (§22) on the ECS instance,
# over SSH. Idempotent: safe to re-run, it removes any prior container first.
#
# Usage: NEO4J_HOST=<ip> NEO4J_PASSWORD=<pw> ./bootstrap-neo4j.sh
set -euo pipefail

: "${NEO4J_HOST:?Set NEO4J_HOST to the ECS public IP (see terraform output neo4j_ecs_public_ip)}"
: "${NEO4J_PASSWORD:?Set NEO4J_PASSWORD to the same value passed as TF_VAR_neo4j_password}"
SSH_USER="${SSH_USER:-root}"

ssh "${SSH_USER}@${NEO4J_HOST}" bash -s <<REMOTE
set -euo pipefail
docker rm -f neo4j 2>/dev/null || true
docker run -d --name neo4j --restart unless-stopped \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/${NEO4J_PASSWORD} \
  -e NEO4J_PLUGINS='["apoc","graph-data-science"]' \
  -v neo4j_data:/data \
  neo4j:5
REMOTE

echo "Neo4j starting on ${NEO4J_HOST}. Browser: http://${NEO4J_HOST}:7474 (login neo4j / your password)"
echo "It can take ~30s after container start before the browser UI responds."
