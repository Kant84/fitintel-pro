# Releases

## fitintel-pro-deploy@v1.5.2 — 2026-09-30
Финальный релиз. Состав и контрольные суммы:

| Файл | Назначение | SHA256 |
|---|---|---|
| fitintel-pro_v1.5.2.zip | код сервера: compose.prod, scripts (install/backup/update), миграции, docs | 4CE475F781F167847378C86E32E1494201B56E335443F65AE3D8CA5ED139B8A0 |
                                                                                                          
| fitintel-prod_v1.5.2.tar (884 МБ) | готовый docker-образ fitintel:prod (`docker load -i`) | c8093134395c3c6cf3dc196a18f520299bd14a47f9182fd0e879c0e7b885a6a4 |
| FitIntelDesktop.exe | desktop-клиент, портабельный (onefile, иконка бренда) | DA6055EA99D1D5E658F6C1D30C352C10066C56BFA1322F0FD5911EE98DC282C4 |
| FitIntelDesktop-Setup_v1.5.2.exe (≈107 МБ) | установщик desktop (ярлык с логотипом, деинсталлятор) | 84745366FE21907E7D502991149C7E3C5550E6BC82A8F190B5BDA93DA63DCD96 |

- Сервер клуба: docs/INSTALL_CLUB.md (5 команд; install.sh генерирует .env с секретами)
- Desktop: Setup.exe (или exe). При первом запуске спрашивает адрес сервера клуба и сохраняет его локально. Одна сборка на все клубы.
- Проверка целостности у получателя: `sha256sum &lt;файл&gt;` / `Get-FileHash &lt;файл&gt;`
- ЭНТ: docs/SKUD_SETUP.md | Лицензии: License Studio (Ed25519, одноразовые, привязка к серверу)

## fitintel-pro-deploy@v1.3.1 — 2026-09-27 (архивная запись, не для установки)
- Архив: fitintel-pro-deploy_v1.3.1.zip (контрольная сумма не сохранена; релиз заменён v1.5.2)