variable "region" {
  description = "Alibaba Cloud region."
  type        = string
  default     = "ap-southeast-1"
}

variable "zone_id" {
  description = "Availability zone within `region`. Must support ECS, Tablestore and ApsaraMQ for Kafka."
  type        = string
  default     = "ap-southeast-1a"
}

variable "name_prefix" {
  description = "Prefix applied to every resource name, so this stack can be told apart from other projects in the same account."
  type        = string
  default     = "symphony"
}

variable "neo4j_password" {
  description = "Password for the Neo4j `neo4j` user. Set via TF_VAR_neo4j_password -- never commit a real value."
  type        = string
  sensitive   = true
}

variable "ssh_public_key" {
  description = "Public key (contents of an id_ed25519.pub / id_rsa.pub) used to SSH into the Neo4j ECS instance for the runbook's bootstrap and health-check steps."
  type        = string
}

variable "allowed_ssh_cidr" {
  description = "CIDR allowed to reach the ECS instance on port 22. Default is intentionally restrictive -- override with your own IP/32, never 0.0.0.0/0."
  type        = string
  default     = "127.0.0.1/32"
}

variable "ecs_instance_type" {
  description = "ECS instance type for the Neo4j host. ecs.e-c1m2.large (2 vCPU / 4 GiB) comfortably runs neo4j:5 with apoc+gds for a demo-scale conflict graph."
  type        = string
  default     = "ecs.e-c1m2.large"
}

variable "kafka_topic_events" {
  description = "Topic name the event bus publishes to -- must match KAFKA_TOPIC_EVENTS in .env.production."
  type        = string
  default     = "symphony-events"
}
