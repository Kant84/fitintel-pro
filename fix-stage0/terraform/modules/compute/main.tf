# =============================================================================
# Модуль: Compute (VM instances)
# =============================================================================

data "yandex_compute_image" "ubuntu" {
  family = "ubuntu-2404-lts"
}

# Service account для VM
resource "yandex_iam_service_account" "vm" {
  name        = "fitintel-${var.environment}-vm-sa"
  description = "Service account for FitIntel ${var.environment} VMs"
}

resource "yandex_resourcemanager_folder_iam_member" "vm" {
  for_each = toset([
    "editor",
    "container-registry.images.puller",
  ])

  folder_id = var.folder_id
  role      = each.value
  member    = "serviceAccount:${yandex_iam_service_account.vm.id}"
}

# VMs
resource "yandex_compute_instance" "vm" {
  for_each = var.instances

  name        = "fitintel-${var.environment}-${each.key}"
  platform_id = "standard-v3"
  zone        = var.zone

  resources {
    cores         = each.value.cores
    memory        = each.value.memory
    core_fraction = 100
  }

  boot_disk {
    initialize_params {
      image_id = data.yandex_compute_image.ubuntu.id
      size     = each.value.disk_size
      type     = "network-ssd"
    }
  }

  network_interface {
    subnet_id          = var.subnet_ids[each.value.subnet_key]
    security_group_ids = [var.security_group_ids[each.value.subnet_key]]
    nat                = each.value.nat
    ip_address         = "10.0.${index(keys(var.subnet_ids), each.value.subnet_key) + 1}.${100 + index(keys(var.instances), each.key)}"
  }

  metadata = {
    ssh-keys = "ubuntu:${file("~/.ssh/id_rsa.pub")}"
    user-data = templatefile("${path.module}/cloud-init.yml", {
      hostname = "fitintel-${var.environment}-${each.key}"
      role     = each.value.role
    })
  }

  labels = {
    environment = var.environment
    role        = each.value.role
    managed_by  = "terraform"
  }

  service_account_id = yandex_iam_service_account.vm.id

  depends_on = [yandex_resourcemanager_folder_iam_member.vm]
}
