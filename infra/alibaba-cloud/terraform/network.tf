resource "alicloud_vpc" "main" {
  vpc_name   = "${var.name_prefix}-vpc"
  cidr_block = "10.0.0.0/16"
}

resource "alicloud_vswitch" "main" {
  vswitch_name = "${var.name_prefix}-vswitch"
  vpc_id       = alicloud_vpc.main.id
  cidr_block   = "10.0.1.0/24"
  zone_id      = var.zone_id
}

resource "alicloud_security_group" "main" {
  security_group_name = "${var.name_prefix}-sg"
  vpc_id              = alicloud_vpc.main.id
}

# SSH -- for the runbook's bootstrap/health-check steps only. Restrict
# `allowed_ssh_cidr` to your own IP; never leave this at 0.0.0.0/0.
resource "alicloud_security_group_rule" "ssh" {
  type              = "ingress"
  ip_protocol       = "tcp"
  port_range        = "22/22"
  security_group_id = alicloud_security_group.main.id
  cidr_ip           = var.allowed_ssh_cidr
}

# Neo4j browser + bolt -- same restricted CIDR as SSH. The dashboard talks to
# the API, never directly to Neo4j, so this doesn't need to be public.
resource "alicloud_security_group_rule" "neo4j_browser" {
  type              = "ingress"
  ip_protocol       = "tcp"
  port_range        = "7474/7474"
  security_group_id = alicloud_security_group.main.id
  cidr_ip           = var.allowed_ssh_cidr
}

resource "alicloud_security_group_rule" "neo4j_bolt" {
  type              = "ingress"
  ip_protocol       = "tcp"
  port_range        = "7687/7687"
  security_group_id = alicloud_security_group.main.id
  cidr_ip           = var.allowed_ssh_cidr
}

# API + dashboard -- public, by design: the deployment-proof recording and
# the judges need to reach these directly. Tighten to a specific CIDR after
# recording if you want to keep the instance up afterward.
resource "alicloud_security_group_rule" "api" {
  type              = "ingress"
  ip_protocol       = "tcp"
  port_range        = "8000/8000"
  security_group_id = alicloud_security_group.main.id
  cidr_ip           = "0.0.0.0/0"
}

resource "alicloud_security_group_rule" "dashboard" {
  type              = "ingress"
  ip_protocol       = "tcp"
  port_range        = "3000/3000"
  security_group_id = alicloud_security_group.main.id
  cidr_ip           = "0.0.0.0/0"
}
