output "neo4j_ecs_public_ip" {
  description = "SSH here to run scripts/bootstrap-neo4j.sh and to reach the API/dashboard once deployed."
  value       = alicloud_instance.neo4j.public_ip
}

output "tablestore_instance_name" {
  value = alicloud_ots_instance.main.name
}

output "tablestore_endpoint" {
  description = "TABLESTORE_ENDPOINT for .env.production. Standard Alibaba Cloud OTS URL convention -- confirm against the console after apply."
  value       = "https://${alicloud_ots_instance.main.name}.${var.region}.ots.aliyuncs.com"
}

output "alikafka_instance_id" {
  description = "The ApsaraMQ for Kafka instance ID. Its actual bootstrap-server endpoint isn't a reliably-named Terraform attribute across provider versions -- read it from the Alibaba Cloud console (Message Queue for Kafka > Instances > this instance > Basic Information) after apply, and put it in .env.production as KAFKA_BOOTSTRAP_SERVERS."
  value       = alicloud_alikafka_instance.main.id
}

output "ram_access_key_id" {
  value = alicloud_ram_access_key.app.id
}

output "ram_access_key_secret" {
  value     = alicloud_ram_access_key.app.secret
  sensitive = true
}
