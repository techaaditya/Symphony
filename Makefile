.PHONY: up down logs build test bench seed clean

NEO4J_USER ?= neo4j
NEO4J_PASSWORD ?= symphony123

# Bring up the full local stack (Neo4j, Redpanda, API, dashboard) and rebuild
# images that changed. Dashboard: http://localhost:3000 · API docs:
# http://localhost:8000/docs · Neo4j browser: http://localhost:7474
up:
	docker compose up --build -d

down:
	docker compose down

logs:
	docker compose logs -f

build:
	docker compose build

# Runs against the local Python venv, not inside a container -- the fast,
# zero-token-cost path (pip install -e ".[dev]" first).
test:
	pytest -q

bench:
	symphony benchmark --n 5

# Drives one real scenario through the running compose stack from the host,
# so the Conflict Graph Explorer (Neo4j) and ledger replay have real data to
# show instead of an empty dashboard. Requires `make up` first. Note: uses
# Redpanda's *external* listener (localhost:19092), not the internal one the
# `api` container uses (redpanda:9092) -- see docker-compose.yml's comment.
seed:
	NEO4J_URI=bolt://localhost:7687 \
	NEO4J_USER=$(NEO4J_USER) \
	NEO4J_PASSWORD=$(NEO4J_PASSWORD) \
	SYMPHONY_BUS=kafka \
	KAFKA_BOOTSTRAP_SERVERS=localhost:19092 \
	symphony sim --scenario wildfire_v3 --seed 42

# Tears the stack down and deletes the Neo4j volume, for a clean-slate demo.
clean:
	docker compose down -v
