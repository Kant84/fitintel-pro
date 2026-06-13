# =============================================================================
# FitIntel Pro — Terraform: Production Environment (Yandex Cloud)
# =============================================================================
# Использование:
#   cd terraform/environments/prod
#   terraform init
#   terraform plan
#   terraform apply
# =============================================================================

terraform {
  required_version = ">= 1.7.0"
  
  required_providers {
    yandex = {
      source  = "yandex-cloud/yandex"
      version = ">= 0.110.0"
    }
  }

  # Хранение state в S3-совместимом бакете (Yandex Object Storage)
  backend "s3" {
    endpoints = {
      s3 = "https://storage.yandexcloud.net"
    }
    bucket = "fitintel-terraform-state"
    key    = "prod/terraform.tfstate"
    region = "ru-central1"
    
    skip_region_validation      = true
    skip_credentials_validation = true
    skip_metadata_api_check     = true
    skip_requesting_account_id  = true
    skip_s3_checksum            = true
  }
}

provider "yandex" {
  zone      = var.zone
  folder_id = var.folder_id
}

# =============================================================================
# Модуль сети
# =============================================================================
module "network" {
  source = "../../modules/network"

  environment     = "prod"
  zone            = var.zone
  vpc_name        = "fitintel-prod-vpc"
  
  # Подсети
  subnets = {
    dmz = {
      cidr = "10.0.1.0/24"
      name = "dmz"
    }
    app = {
      cidr = "10.0.2.0/24" 
      name = "app"
    }
    db = {
      cidr = "10.0.3.0/24"
      name = "db"
    }
    monitoring = {
      cidr = "10.0.4.0/24"
      name = "monitoring"
    }
  }
}

# =============================================================================
# Модуль вычислительных ресурсов
# =============================================================================
module "compute" {
  source = "../../modules/compute"

  environment   = "prod"
  zone          = var.zone
  network_id    = module.network.vpc_id
  subnet_ids    = module.network.subnet_ids
  
  # VM конфигурации
  instances = {
    # API серверы (2 шт для HA)
    api-1 = {
      subnet_key = "app"
      cores      = 4
      memory     = 8
      disk_size  = 50
      image_family = "ubuntu-2404-lts"
      nat        = false
      role       = "api"
    }
    api-2 = {
      subnet_key = "app"
      cores      = 4
      memory     = 8
      disk_size  = 50
      image_family = "ubuntu-2404-lts"
      nat        = false
      role       = "api"
    }
    
    # База данных (Master)
    db-master = {
      subnet_key = "db"
      cores      = 4
      memory     = 16
      disk_size  = 100
      image_family = "ubuntu-2404-lts"
      nat        = false
      role       = "db-master"
    }
    
    # База данных (Replica)
    db-replica = {
      subnet_key = "db"
      cores      = 4
      memory     = 16
      disk_size  = 100
      image_family = "ubuntu-2404-lts"
      nat        = false
      role       = "db-replica"
    }
    
    # Мониторинг
    monitoring = {
      subnet_key = "monitoring"
      cores      = 4
      memory     = 8
      disk_size  = 50
      image_family = "ubuntu-2404-lts"
      nat        = true
      role       = "monitoring"
    }
  }
}

# =============================================================================
# Балансировщик нагрузки (ALB)
# =============================================================================
resource "yandex_alb_load_balancer" "main" {
  name        = "fitintel-prod-alb"
  network_id  = module.network.vpc_id
  
  allocation_policy {
    location {
      zone_id   = var.zone
      subnet_id = module.network.subnet_ids["dmz"]
    }
  }

  listener {
    name = "https"
    endpoint {
      address {
        subnet_id = module.network.subnet_ids["dmz"]
      }
      ports = [443]
    }
    tls {
      default_handler {
        http_handler {
          http_router_id = yandex_alb_http_router.main.id
        }
        certificate_ids = [yandex_cm_certificate.main.id]
      }
    }
  }

  listener {
    name = "http-redirect"
    endpoint {
      address {
        subnet_id = module.network.subnet_ids["dmz"]
      }
      ports = [80]
    }
    http {
      handler {
        http_router_id = yandex_alb_http_router.redirect.id
      }
    }
  }
}

resource "yandex_alb_http_router" "main" {
  name = "fitintel-prod-router"
}

resource "yandex_alb_http_router" "redirect" {
  name = "fitintel-prod-redirect"
}

# =============================================================================
# DNS
# =============================================================================
resource "yandex_dns_zone" "main" {
  name        = "fitintel-prod-zone"
  zone        = "${var.domain}."
  public      = true
}

resource "yandex_dns_recordset" "api" {
  zone_id = yandex_dns_zone.main.id
  name    = "api.${var.domain}."
  type    = "A"
  ttl     = 300
  data    = [yandex_alb_load_balancer.main.listener[0].endpoint[0].address[0].subnet_id]
}

# =============================================================================
# Certificate Manager
# =============================================================================
resource "yandex_cm_certificate" "main" {
  name    = "fitintel-prod-cert"
  domains = [var.domain, "*.${var.domain}"]

  managed {
    challenge_type = "DNS_C01"
  }
}

# =============================================================================
# Output
# =============================================================================
output "vpc_id" {
  value = module.network.vpc_id
}

output "subnet_ids" {
  value = module.network.subnet_ids
}

output "vm_ips" {
  value = module.compute.internal_ips
}

output "alb_ip" {
  value = yandex_alb_load_balancer.main.listener[0].endpoint[0].address[0].subnet_id
}
