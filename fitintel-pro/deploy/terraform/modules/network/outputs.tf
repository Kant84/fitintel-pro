output "vpc_id" {
  description = "ID созданной VPC"
  value       = yandex_vpc_network.main.id
}

output "subnet_ids" {
  description = "Map ID подсетей"
  value       = { for k, v in yandex_vpc_subnet.subnets : k => v.id }
}

output "security_group_ids" {
  description = "Map ID security groups"
  value = {
    dmz        = yandex_vpc_security_group.dmz.id
    app        = yandex_vpc_security_group.app.id
    db         = yandex_vpc_security_group.db.id
    monitoring = yandex_vpc_security_group.monitoring.id
  }
}
