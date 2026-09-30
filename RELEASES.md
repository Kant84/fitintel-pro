# Releases

## fitintel-pro-deploy@v1.5.2 — 2026-09-30
Финальный релиз. Состав и контрольные суммы:

| Файл | Назначение | SHA256 |
|---|---|---|
| fitintel-pro_v1.5.2.zip (код) | сервер: compose.prod, scripts (install/backup/update), миграции, docs | 4CE475F781F167847378C86E32E1494201B56E335443F65AE3D8CA5ED139B8A0 |
| fitintel-prod_v1.5.2.tar (884 МБ) | готовый docker-образ fitintel:prod (docker load) | c8093134395c3c6cf3dc196a18f520299bd14a47f9182fd0e879c0e7b885a6a4 |
| FitIntelDesktop.exe / FitIntelDesktop-Setup_v1.5.2.exe | desktop-клиент для рабочих мест клуба | &lt;хэш exe — Get-FileHash&gt; |

- Установка сервера клуба: docs/INSTALL_CLUB.md (5 команд, install.sh генерирует .env с секретами)
- Установка desktop: установщик (или exe) + client_settings.json с api_base клуба
- Контроль целостности у получателя: `sha256sum &lt;файл&gt;` / `Get-FileHash &lt;файл&gt;`
- Поддержка ЭНТ: docs/SKUD_SETUP.md; лицензии: License Studio (Ed25519, одноразовые)

## fitintel-pro-deploy@v1.3.1 — 2026-09-27 (архивная запись)
- Архив: fitintel-pro-deploy_v1.3.1.zip
- SHA256: a1JJs+6qLMUndq8mp6DSZgaSirF0OVqBN9c8DU5ka3w