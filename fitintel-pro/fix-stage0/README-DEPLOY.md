# FitIntel Pro — Stage 0: Исправления + Инфраструктура

## Что сделано

### Stage 0: Исправление проекта (1-2 дня)

| Файл | Назначение |
|------|------------|
| `fix_project.py` | Автоматически исправляет все критические проблемы |

**Что исправляет:**
- `_init_.py` → `__init__.py` (опечатка)
- Создаёт 21 `__init__.py` в пакетах
- Удаляет 9 временных/отладочных файлов
- Создаёт `.gitignore` для Python проекта
- Удаляет дублирование `app/utils/qr.py`
- Создаёт `app/middleware/` и `app/dto/`

### Stage 1: Инфраструктура E7-E10

| Компонент | Статус | Файлы |
|-----------|--------|-------|
| **Terraform** | Готов | `terraform/environments/prod/` + модули network, compute |
| **Ansible** | Готов | `ansible/playbooks/site.yml` + роли common, zabbix_agent |
| **Zabbix** | Готов | `monitoring/docker-compose.monitoring.yml` |
| **Prometheus** | Готов | `monitoring/prometheus/prometheus.yml` + rules |
| **Grafana** | Готов | `monitoring/grafana/provisioning/` |

---

## Быстрый старт

### Шаг 1: Исправить проект

```bash
# Перейти в корень проекта
cd /путь/к/FitNexus-AI

# Скопировать fix_project.py в корень
cp /путь/к/fix_project.py .

# Запустить исправления
python fix_project.py .

# Проверить git status
git status

# Коммит
git add -A
git commit -m "Stage 0: Fix critical issues - __init__.py, .gitignore, temp files"
```

### Шаг 2: Развернуть инфраструктуру (Terraform)

```bash
# 1. Установить Terraform и настроить Yandex Cloud CLI
# https://yandex.cloud/ru/docs/cli/quickstart

# 2. Настроить провайдер
export YC_TOKEN=$(yc iam create-token)
export YC_FOLDER_ID=$(yc config get folder-id)

# 3. Инициализация
cd terraform/environments/prod
cp terraform.tfvars.example terraform.tfvars
# Отредактировать terraform.tfvars — указать folder_id и домен

# 4. Создать S3 бакет для state (один раз)
# yc storage bucket create --name fitintel-terraform-state

# 5. Развертывание
terraform init
terraform plan
terraform apply

# 6. Получить IP-адреса
terraform output
```

### Шаг 3: Настроить серверы (Ansible)

```bash
# 1. Установить Ansible
pip install ansible

# 2. Настроить inventory
cd ansible
vim inventory/yandex.yml
# Заменить YOUR_MONITORING_EXTERNAL_IP на реальный IP

# 3. Настроить SSH (копируем ключ на bastion)
ssh-copy-id ubuntu@<MONITORING_EXTERNAL_IP>

# 4. Запуск всего
ansible-playbook -i inventory/yandex.yml playbooks/site.yml

# 5. Или по частям:
ansible-playbook -i inventory/yandex.yml playbooks/site.yml --tags common
ansible-playbook -i inventory/yandex.yml playbooks/site.yml --tags zabbix
ansible-playbook -i inventory/yandex.yml playbooks/site.yml --tags monitoring
```

### Шаг 4: Запустить мониторинг

```bash
# На monitoring сервере:
cd /opt/fitintel/monitoring
cp .env.monitoring.example .env.monitoring
# Заполнить пароли

docker compose -f docker-compose.monitoring.yml up -d

# Проверить:
docker compose ps
curl http://localhost:9090  # Prometheus
curl http://localhost:3000  # Grafana (admin/admin)
curl http://localhost:8080  # Zabbix
```

### Шаг 5: Деплой приложения

```bash
# На API серверах:
cd /opt/fitintel/app
git clone <your-repo> .
cp .env.example .env
# Заполнить DATABASE_URL, REDIS_URL, SECRET_KEY

docker compose -f docker-compose.prod.yml up -d

# Проверить:
docker compose ps
curl http://localhost:8000/health
```

---

## Структура файлов

```
fix-stage0/
├── fix_project.py              # Автоисправление проекта
├── README-DEPLOY.md            # Этот файл
├──
├── terraform/
│   ├── environments/
│   │   └── prod/
│   │       ├── main.tf
│   │       ├── variables.tf
│   │       └── terraform.tfvars.example
│   └── modules/
│       ├── network/            # VPC, подсети, Security Groups
│       └── compute/            # VM, cloud-init
│
├── ansible/
│   ├── ansible.cfg
│   ├── inventory/
│   │   └── yandex.yml
│   ├── playbooks/
│   │   └── site.yml
│   └── roles/
│       ├── common/             # Базовая настройка
│       ├── zabbix_agent/       # Zabbix Agent 2
│       ├── nginx/              # Load balancer
│       ├── postgresql/         # PostgreSQL
│       ├── prometheus_exporter/# Node/Postgres exporters
│       ├── zabbix_server/      # Zabbix Server
│       ├── prometheus/         # Prometheus
│       └── grafana/            # Grafana dashboards
│
└── monitoring/
    ├── docker-compose.monitoring.yml
    ├── prometheus/
    │   ├── prometheus.yml
    │   └── rules/
    │       └── fitintel.yml
    ├── grafana/
    │   └── provisioning/
    │       └── datasources/
    │           └── prometheus.yml
    └── .env.monitoring.example
```

---

## Тестирование после каждого этапа

### После Stage 0 (исправления)
```bash
# Проверка импортов
python -c "from app.main import app; print('✓ Main OK')"
python -c "from app.db.session import get_db; print('✓ DB OK')"
python -c "from app.models.client import Client; print('✓ Models OK')"
python -c "from app.services.auth_service import AuthService; print('✓ Services OK')"

# Запуск тестов
pytest tests/ -v
```

### После Terraform
```bash
terraform output  # Проверить IP-адреса
ssh ubuntu@<monitoring-ip> "hostname"  # Проверить SSH
```

### После Ansible
```bash
ansible all -i inventory/yandex.yml -m ping  # Проверить связь
ansible monitoring -i inventory/yandex.yml -m shell -a "docker ps"  # Docker работает
```

### После деплоя
```bash
curl https://api.fitintel.ru/health  # Health check
curl https://api.fitintel.ru/docs     # Swagger/OpenAPI
```

---

## Что дальше (E9-E14)

| Этап | Что делать | Срок |
|------|-----------|------|
| **E9** | 152-ФЗ: шифрование Vault, аудит-логи | 2-3 дня |
| **E10** | HA: PostgreSQL репликация, бэкапы wal-g | 2-3 дня |
| **E11** | Документы: PDF-генерация, ЭЦП | 3-5 дней |
| **E12** | 1C интеграция | 3-5 дней |
| **E13** | Admin Panel (React) | 1-2 недели |
| **E14** | Client Cabinet PWA | 1-2 недели |

---

*FixIntel Pro — Автоматизация фитнес-клубов*
