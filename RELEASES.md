# Releases

## fitintel-pro-deploy@v1.5.2 — 2026-09-30 (текущий)

| Файл | Назначение | SHA256 |
|---|---|---|
| fitintel-pro_v1.5.2.zip | код сервера: compose.prod, scripts (install/backup/update), миграции, docs | 78F70ECA82475E38110300A4EDF8CDDCAC29AE9F0564A3793502B39D577EA247 |
| fitintel-prod_v1.5.2.tar (≈880 МБ) | готовый docker-образ fitintel:prod (`docker load -i`) | efae72ac40ac08fce8d4cd42a6d57254642c4175fd1f43333c0d9943b11f2e56 |
| FitIntelDesktop.exe | desktop-клиент, портабельный (onefile, иконка бренда) | 7F70B15698A097F9D05775F887ADE2825413C852015E079E4670F22AFA2376BD |
| FitIntelDesktop-Setup_v1.5.2.exe (≈107 МБ) | установщик desktop (ярлык с логотипом, деинсталлятор) | E188F3FFACC65D738619DB9726227D884C7ECB2F4AB6B2A61CBC7E236E4B83AD |

**Состав релиза:** одноразовые Ed25519-лицензии (License Studio, привязка к серверу, чистая активация первого запуска) · ЭНТ «подтверждение доступа» реалтайм (docs/SKUD_SETUP.md) · RFID прямой USB + виджет монитора · Face ID (камера, настройки клуба, опциональное хранение фото, анти-спуфинг/liveness задел) · строгая модель ролей (9 профилей, экраны по матрице) · аудит «История» с сроком хранения · центр отчётов (10 отчётов + CSV) · бухгалтерия (ПКО/РКО, ОСВ, P&L) · мониторинг · авто-бэкапы (хост, через контейнер db) · прод-комплект (install/backup/update.sh, INSTALL_CLUB.md, compose.prod).

- Сервер клуба: docs/INSTALL_CLUB.md (5 команд; install.sh генерирует .env с секретами)
- Desktop: Setup.exe; при первом запуске спрашивает адрес сервера и запоминает его. Одна сборка на все клубы.
- Проверка целостности: `sha256sum &lt;файл&gt;` / `Get-FileHash &lt;файл&gt;`

## fitintel-pro-deploy@v1.3.1 — 2026-09-27 (архивная запись, не для установки)
- Архив: fitintel-pro-deploy_v1.3.1.zip (контрольная сумма не сохранена; релиз заменён v1.5.2)