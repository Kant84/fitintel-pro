# =============================================================================
# Модуль: Network (VPC + Subnets + NAT)
# =============================================================================

resource "yandex_vpc_network" "main" {
  name = var.vpc_name
}

# NAT-шлюз для выхода в интернет из приватных подсетей
resource "yandex_vpc_gateway" "nat" {
  name = "${var.vpc_name}-nat"
  shared_egress_gateway {}
}

# Таблица маршрутизации для NAT
resource "yandex_vpc_route_table" "nat" {
  name       = "${var.vpc_name}-nat-route"
  network_id = yandex_vpc_network.main.id

  static_route {
    destination_prefix = "0.0.0.0/0"
    gateway_id         = yandex_vpc_gateway.nat.id
  }
}

# Подсети
resource "yandex_vpc_subnet" "subnets" {
  for_each = var.subnets

  name           = "${var.vpc_name}-${each.value.name}"
  zone           = var.zone
  network_id     = yandex_vpc_network.main.id
  v4_cidr_blocks = [each.value.cidr]
  route_table_id = yandex_vpc_route_table.nat.id

  labels = {
    environment = var.environment
    subnet      = each.value.name
  }
}

# Security Group: DMZ (Nginx)
resource "yandex_vpc_security_group" "dmz" {
  name       = "${var.vpc_name}-dmz-sg"
  network_id = yandex_vpc_network.main.id

  # HTTPS входящий
  ingress {
    protocol       = "TCP"
    port           = 443
    v4_cidr_blocks = ["0.0.0.0/0"]
  }

  # HTTP входящий (для redirect)
  ingress {
    protocol       = "TCP"
    port           = 80
    v4_cidr_blocks = ["0.0.0.0/0"]
  }

  # Исходящий
  egress {
    protocol       = "ANY"
    v4_cidr_blocks = ["0.0.0.0/0"]
  }
}

# Security Group: APP (FastAPI)
resource "yandex_vpc_security_group" "app" {
  name       = "${var.vpc_name}-app-sg"
  network_id = yandex_vpc_network.main.id

  # Внутренний трафик от DMZ
  ingress {
    protocol          = "TCP"
    port              = 8000
    predefined_target = "self_security_group"
  }

  # Redis
  ingress {
    protocol          = "TCP"
    port              = 6379
    predefined_target = "self_security_group"
  }

  # Исходящий
  egress {
    protocol       = "ANY"
    v4_cidr_blocks = ["0.0.0.0/0"]
  }
}

# Security Group: DB (PostgreSQL)
resource "yandex_vpc_security_group" "db" {
  name       = "${var.vpc_name}-db-sg"
  network_id = yandex_vpc_network.main.id

  # PostgreSQL только из APP
  ingress {
    protocol       = "TCP"
    port           = 5432
    v4_cidr_blocks = [for s in var.subnets : s.cidr if s.name == "app"]
  }

  # Исходящий
  egress {
    protocol       = "ANY"
    v4_cidr_blocks = ["0.0.0.0/0"]
  }
}

# Security Group: Monitoring
resource "yandex_vpc_security_group" "monitoring" {
  name       = "${var.vpc_name}-mon-sg"
  network_id = yandex_vpc_network.main.id

  # Zabbix
  ingress {
    protocol       = "TCP"
    port           = 10050
    v4_cidr_blocks = [for s in var.subnets : s.cidr]
  }

  # Zabbix active
  ingress {
    protocol       = "TCP"
    port           = 10051
    v4_cidr_blocks = [for s in var.subnets : s.cidr]
  }

  # Prometheus
  ingress {
    protocol       = "TCP"
    port           = 9090
    v4_cidr_blocks = [for s in var.subnets : s.cidr]
  }

  # Grafana
  ingress {
    protocol       = "TCP"
    port           = 3000
    v4_cidr_blocks = ["0.0.0.0/0"]
  }

  # SSH через VPN only
  ingress {
    protocol       = "TCP"
    port           = 22
    v4_cidr_blocks = ["10.0.0.0/8"]
  }

  # Исходящий
  egress {
    protocol       = "ANY"
    v4_cidr_blocks = ["0.0.0.0/0"]
  }
}
