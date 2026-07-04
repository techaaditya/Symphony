# ApsaraMQ for Kafka -- backs KafkaEventBus (symphony/bus/kafka_bus.py).
#
# NOTE ON THIS FILE: `alicloud_alikafka_instance`'s enum-valued fields
# (`deploy_type`, `disk_type`, `spec_type`, `paid_type`) have changed meaning
# across provider/API versions, and instance provisioning is genuinely slow
# (10-30 min) and billed from creation. Treat the values below as a
# documented starting point, not a verified-working config -- confirm them
# against the current alicloud provider docs and Alibaba Cloud console
# before `terraform apply`, per the design doc's own reminder to verify
# current service specifics before locking in a budget plan.

resource "alicloud_alikafka_instance" "main" {
  name           = "${var.name_prefix}-kafka"
  partition_num  = 50
  disk_type      = 1 # 1 = efficient cloud disk
  disk_size      = 500
  deploy_type    = 5 # VPC deployment
  io_max         = 20
  vswitch_id     = alicloud_vswitch.main.id
  security_group = alicloud_security_group.main.id
  paid_type      = "PostPaid"
}

resource "alicloud_alikafka_topic" "events" {
  instance_id = alicloud_alikafka_instance.main.id
  topic       = var.kafka_topic_events
  remark      = "Symphony simulator event stream"
}
