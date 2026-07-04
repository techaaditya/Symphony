# A dedicated RAM user for the deployed API to authenticate to Tablestore and
# ApsaraMQ for Kafka with, instead of the account's root/primary credentials.
#
# The attached policies are the broad system-managed ones for simplicity in a
# hackathon deploy -- scope these down to a custom policy naming this exact
# OTS instance / Kafka instance ARN before using this pattern beyond a demo.

resource "alicloud_ram_user" "app" {
  name = "${var.name_prefix}-app"
}

resource "alicloud_ram_user_policy_attachment" "ots" {
  user_name   = alicloud_ram_user.app.name
  policy_name = "AliyunOTSFullAccess"
  policy_type = "System"
}

resource "alicloud_ram_user_policy_attachment" "kafka" {
  user_name   = alicloud_ram_user.app.name
  policy_name = "AliyunKafkaFullAccess"
  policy_type = "System"
}

resource "alicloud_ram_access_key" "app" {
  user_name = alicloud_ram_user.app.name
}
