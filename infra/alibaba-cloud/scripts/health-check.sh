#!/bin/bash
# Verifies every deployed service actually responds. Run after
# bootstrap-neo4j.sh and `docker compose -f docker-compose.prod.yml up`.
#
# Usage: HOST=<ecs-public-ip> ./health-check.sh
set -euo pipefail

: "${HOST:?Set HOST to the ECS public IP (terraform output neo4j_ecs_public_ip)}"

check() {
  local name="$1" url="$2"
  if curl -fsS -o /dev/null --max-time 5 "$url"; then
    echo "OK    $name  ($url)"
  else
    echo "FAIL  $name  ($url)"
    return 1
  fi
}

status=0
check "Neo4j browser" "http://${HOST}:7474" || status=1
check "API openapi.json" "http://${HOST}:8000/openapi.json" || status=1
check "Dashboard" "http://${HOST}:3000" || status=1

exit "$status"
