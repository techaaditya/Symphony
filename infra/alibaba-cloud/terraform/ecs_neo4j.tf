data "alicloud_images" "ubuntu" {
  name_regex  = "^ubuntu_22_04_x64"
  owners      = "system"
  most_recent = true
}

resource "alicloud_key_pair" "main" {
  key_pair_name = "${var.name_prefix}-key"
  public_key    = var.ssh_public_key
}

# Installs Docker only. The actual `docker run neo4j:5 ...` (doc §22) and the
# `docker compose up` for the api/dashboard containers are run explicitly via
# SSH from ../scripts/, per ../DEPLOY_RUNBOOK.md -- kept out of user_data so
# the exact commands that stood up the demo are inspectable/reproducible by
# hand, not buried in cloud-init logs.
locals {
  user_data = <<-EOT
    #!/bin/bash
    set -euo pipefail
    apt-get update -y
    apt-get install -y ca-certificates curl gnupg
    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
    chmod a+r /etc/apt/keyrings/docker.asc
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
      > /etc/apt/sources.list.d/docker.list
    apt-get update -y
    apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
    systemctl enable --now docker
    docker volume create neo4j_data
  EOT
}

resource "alicloud_instance" "neo4j" {
  instance_name              = "${var.name_prefix}-neo4j"
  instance_type              = var.ecs_instance_type
  image_id                   = data.alicloud_images.ubuntu.images[0].id
  security_groups            = [alicloud_security_group.main.id]
  vswitch_id                 = alicloud_vswitch.main.id
  key_name                   = alicloud_key_pair.main.key_pair_name
  system_disk_category       = "cloud_essd"
  system_disk_size           = 40
  internet_charge_type       = "PayByTraffic"
  internet_max_bandwidth_out = 10
  user_data                  = base64encode(local.user_data)

  tags = {
    project = var.name_prefix
    role    = "neo4j-and-app-host"
  }
}
