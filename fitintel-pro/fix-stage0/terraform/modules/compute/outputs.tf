output "instance_ids" {
  value = { for k, v in yandex_compute_instance.vm : k => v.id }
}

output "internal_ips" {
  value = { for k, v in yandex_compute_instance.vm : k => v.network_interface[0].ip_address }
}

output "external_ips" {
  value = { for k, v in yandex_compute_instance.vm : k => v.network_interface[0].nat_ip_address if v.network_interface[0].nat }
}
