terraform {
  required_version = ">= 1.5"

  required_providers {
    alicloud = {
      source  = "aliyun/alicloud"
      version = "~> 1.230"
    }
  }
}

provider "alicloud" {
  region = var.region
  # Credentials: set via ALICLOUD_ACCESS_KEY / ALICLOUD_SECRET_KEY env vars
  # (never committed) -- see ../DEPLOY_RUNBOOK.md.
}
