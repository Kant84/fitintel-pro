# Presentation Outline

## Page 1 [cover]
- **Title**: FitNexus AI
- **Content**: Fitness OS: Модульная серверная платформа управления фитнес-клубом | Техническое задание v2.0

## Page 2 [table_of_contents]
- **Title**: Содержание
- **Content**: 1. Общие сведения и текущий статус; 2. Архитектура и технологический стек; 3. Модули платформы; 4. Инфраструктура и автоматизация; 5. Мониторинг и безопасность; 6. Этапы разработки и план действий

## Page 3 [chapter]
- **Title**: 01: Общие сведения
- **Content**: Проект, статус реализации и ключевые цели

## Page 4 [content]
- **Title**: FitNexus AI — Fitness OS: единая система для управления фитнес-клубом
- **Content**: Раздел 1 "Общие сведения" и Раздел 2 "Статус реализации". FitNexus AI — это модульная серверная платформа (Fitness OS), объединяющая CRM, СКУД, финансы, документы, аналитику и ИИ. На текущий момент реализовано 6 этапов (E0–E6): Foundation, Infrastructure, Core Platform, CRM, Access Control, Visits, Finance. ~100+ API endpoints, 25+ таблиц БД, 7 ролей пользователей. Текущий фокус — этапы E7–E10: Infrastructure as Code, Monitoring, Security, High Availability.

## Page 5 [chapter]
- **Title**: 02: Архитектура и стек
- **Content**: Технологический стек, структура проекта, слои приложения

## Page 6 [content]
- **Title**: Python 3.12 + FastAPI + PostgreSQL + Redis + React — зрелый стек для enterprise
- **Content**: Раздел 5.1 "Технологический стек". Backend: Python 3.12 + FastAPI. База данных: PostgreSQL 16 + SQLAlchemy 2 + Alembic. Кэш/Очереди: Redis 7 + Celery. Веб-сервер: Nginx (reverse proxy, SSL). Контейнеризация: Docker + Docker Compose (MVP) → Kubernetes (Enterprise). Инфраструктура: Terraform + Ansible (IaC). Мониторинг: Zabbix + Prometheus + Grafana. CI/CD: GitLab CI/CD.

## Page 7 [content]
- **Title**: 5 слоев архитектуры: от клиента до инфраструктурного мониторинга
- **Content**: Раздел 5.3 "Схема работы ПО". Слой 1 — Клиентский (Web UI React, PWA, Инфотерминалы KERONG). Слой 2 — Шлюз (Nginx + SSL/TLS 1.3 + ModSecurity WAF + Rate limiting). Слой 3 — Прикладной (FastAPI: Core, CRM, Finance, Visits, Access Control, Documents, AI). Слой 4 — Данные/Кэш (PostgreSQL Master+Replica, Redis, Celery). Слой 5 — Инфраструктура (Zabbix, Prometheus, Grafana, Terraform, Ansible, GitLab CI/CD).

## Page 8 [chapter]
- **Title**: 03: Модули платформы
- **Content**: Реализованные и запланированные бизнес-модули

## Page 9 [content]
- **Title**: 6 модулей реализовано: от аутентификации до финансовой кассы
- **Content**: Раздел 4.1–4.5. Core Platform: JWT-аутентификация, RBAC (7 ролей), Guard-правила, аудит, Explain Access. CRM: клиенты, тарифы, абонементы (ACTIVE/FROZEN/EXPIRED/CANCELLED), timeline, история статусов. Visits: фиксация входа/выхода, активные посещения, статистика по часам/дням/зонам, фоновые задачи. Access Control: QR/RFID, KERONG замки (OFFLINE/ONLINE), шкафчики, офлайн-кэш, журнал доступа. Finance: кошельки, транзакции, платежи (11 платёжных систем), чеки ОФД, кассовые смены, Z-отчёты, продажи.

## Page 10 [content]
- **Title**: 10+ модулей в плане: рекурренты, лояльность, ИИ-аналитика, корпоративные продажи
- **Content**: Раздел 4.6–4.19. Recurring Payments (подписки с гибким графиком). Online Booking Widget (запись на сайт/карты/соцсети). Buddy Referrals (реферальная программа). AI Reactivation (реактивация "спящих" клиентов). Niche Templates (йога, растяжка, танцы, единоборства). Corporate Sales (B2B абонементы). Loyalty & Gamification (уровни Bronze→Platinum, бейджи, баллы). Seasonal Campaigns (автоматический маркетинг по сезонам). Trainer Analytics (загрузка, удержание). AI Analytics (прогноз оттока, сегментация, heatmap).

## Page 11 [chapter]
- **Title**: 04: Инфраструктура и автоматизация
- **Content**: Terraform, Ansible, CI/CD — инфраструктура как код

## Page 12 [content]
- **Title**: Terraform + Ansible + GitLab CI/CD: полная автоматизация развёртывания
- **Content**: Раздел 6 "Требования к инфраструктуре". Terraform: VPC, подсети, NAT, VMs в Yandex Cloud, ALB, DNS, IAM, S3 state с блокировкой. Все изменения только через Terraform (запрет ручных правок). Ansible: hardening ОС, Docker CE, Nginx, firewall, агенты мониторинга, logrotate. Идемпотентные playbooks, ansible-vault для секретов, динамический inventory из Terraform. CI/CD Pipeline: test → build → security-scan → deploy-staging → deploy-production. Trivy (сканирование образов), Bandit (Python SAST).

## Page 13 [content]
- **Title**: Автоустановка агентов: новый сервер = мониторинг + алерты за 5 минут
- **Content**: Раздел 6.3 "Автоустановка агентов мониторинга". Zabbix Agent 2: автоматическая установка через Ansible, авто-регистрация через API, шаблоны (Linux, Docker, PostgreSQL, Nginx), PSK/TLS шифрование. Prometheus Node Exporter: CPU, RAM, диск, сеть, systemd. cAdvisor: метрики Docker-контейнеров. PostgreSQL Exporter: коннекты, медленные запросы, репликация. При добавлении сервера: Terraform → Ansible → автоагенты → Grafana dashboards.

## Page 14 [chapter]
- **Title**: 05: Мониторинг и безопасность
- **Content**: Zabbix + Prometheus/Grafana, 152-ФЗ, защита платежных данных

## Page 15 [content]
- **Title**: Zabbix + Prometheus + Grafana: двухуровневый мониторинг всей инфраструктуры
- **Content**: Раздел 7 "Требования к мониторингу". Zabbix (инфраструктура): CPU/RAM/диск каждую минуту, Docker-контейнеры, PostgreSQL репликация, Nginx 5xx, SSL-сертификаты, СКУД-устройства. Алерты: Telegram + Email, эскалация → SMS через 15 мин. Prometheus (приложение): RPS, latency p50/p95/p99, ошибки, активные пользователи, платежи, длительность посещений, точность ИИ. Grafana: 5 дашбордов (Infrastructure, API Performance, Business Metrics, Database, Security).

## Page 16 [content]
- **Title**: 152-ФЗ + PCI DSS: шифрование, сегментация, аудит, защита от взлома
- **Content**: Раздел 8 "Требования к безопасности". Сеть: DMZ/APP/DB/MON подсети, firewall (только 80/443 снаружи, 22 через WireGuard VPN), DDoS-защита Yandex Cloud. Приложение: ModSecurity WAF, rate limiting (100 req/min), fail2ban (5 попыток → бан 1ч), HSTS/CSP. Данные: AES-256 для бэкапов, TLS 1.3, bcrypt (12 rounds), HashiCorp Vault. 152-ФЗ: шифрование ПДн, разделение PII, журнал аудита 5 лет, право на забвение. PCI DSS: не хранить CVV, токены платёжных систем, изоляция платёжного модуля.

## Page 17 [chapter]
- **Title**: 06: План действий
- **Content**: Этапы разработки, риски, команда и бюджет

## Page 18 [content]
- **Title**: 20 этапов: от Foundation до нативных мобильных приложений
- **Content**: Раздел 17 "Этапы разработки". ✅ E0–E6 (100%): Foundation, Infrastructure, Core, CRM, Access Control, Visits, Finance. ⚙️ E7–E10 (ТЕКУЩИЕ): IaC, Monitoring, Security, HA. 🔄 E11–E14: Documents, 1C Integration, Admin Panel, Client Cabinet. 📋 E15–E20: Recurring & Booking, Loyalty & Referrals, Corporate & Niche, AI Analytics, Seasonal & Reactivation, Native Apps. Рекомендация: сначала закрыть E7–E10, параллельно E11–E14, затем бизнес-фичи.

## Page 19 [content]
- **Title**: Команда 4–5 человек, бюджет 2–5M ₽, запуск первого клиента через 3 месяца
- **Content**: Разделы 19–20. Команда: 1–2 Backend (Python/FastAPI), 0.5–1 DevOps (Terraform/Ansible/Zabbix), 1 Frontend (React/PWA), 0.5 QA, 0.5 Product Owner. Бюджет: разработка 2–5M ₽, Yandex Cloud 100–300K ₽/год, лицензии 50–100K ₽, поддержка 50–100K ₽/мес. Главный риск: перегрузка функционалом (~20 модулей для 1–2 разработчиков = 2–3 года). MVP: 7 модулей, первый клиент на 60% готовности.

## Page 20 [final]
- **Title**: FitNexus AI — готов к запуску первого клиента
- **Content**: Технически грамотная платформа с правильным стеком, модульной архитектурой и осознанным подходом к безопасности. 60% готовности к первому клиенту. Осталось: инфраструктурная автоматизация, мониторинг, Admin Panel и Client Cabinet. FitNexus AI v2.0 | 29 мая 2026
