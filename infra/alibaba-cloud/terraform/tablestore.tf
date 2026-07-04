# Backs TablestoreBlackboardStore (symphony/blackboard/tablestore_store.py).
# Table name, primary-key column and type must match that module's
# TABLE_NAME / _PRIMARY_KEY_COLUMN exactly -- Tablestore only ever stores a
# single row (the latest world-state snapshot), so no throughput tuning is
# needed beyond the smallest capacity tier.

resource "alicloud_ots_instance" "main" {
  # OTS instance names are capped at 16 bytes -- "${name_prefix}-blackboard"
  # (20 chars) is too long, unlike every other resource name in this stack.
  name          = "${var.name_prefix}-ots"
  description   = "Symphony blackboard store -- doc §11"
  accessed_by   = "Any"
  instance_type = "Capacity"

  tags = {
    project = var.name_prefix
  }
}

resource "alicloud_ots_table" "blackboard" {
  instance_name = alicloud_ots_instance.main.name
  table_name    = "symphony_blackboard"

  primary_key {
    name = "id"
    type = "String"
  }

  time_to_live = -1 # never expire -- this table holds live state, not events
  max_version  = 1  # only the latest snapshot matters
}
