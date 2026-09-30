# Releases

## fitintel-pro-deploy@v1.5.2 — 2026-09-30
Финальный релиз. Состав и контрольные суммы:

| Файл | Назначение | SHA256 |
|---|---|---|
| fitintel-pro_v1.5.2.zip | код сервера: compose.prod, scripts (install/backup/update), миграции, docs | 4CE475F781F167847378C86E32E1494201B56E335443F65AE3D8CA5ED139B8A0 |
                                                                                                          
| fitintel-prod_v1.5.2.tar (884 МБ) | готовый docker-образ fitintel:prod (`docker load -i`) | c8093134395c3c6cf3dc196a18f520299bd14a47f9182fd0e879c0e7b885a6a4 |
| FitIntelDesktop.exe | desktop-клиент, портабельный (onefile, иконка бренда) | 736CD87A1458D02384734540DDF83A20A660F9D470B834985677995C693615F6 |
| FitIntelDesktop-Setup_v1.5.2.exe (≈107 МБ) | установщик desktop (ярлык с логотипом, деинсталлятор) | CC10097DCFCDFFE55D71A9360E4D6B219A3166D23E26B3165180A3CB5AC36F58 |

- Сервер клуба: docs/INSTALL_CLUB.md (5 команд; install.sh генерирует .env с секретами)
- Desktop: Setup.exe (или exe). При первом запуске спрашивает адрес сервера клуба и сохраняет его локально. Одна сборка на все клубы.
- Проверка целостности у получателя: `sha256sum &lt;файл&gt;` / `Get-FileHash &lt;файл&gt;`
- ЭНТ: docs/SKUD_SETUP.md | Лицензии: License Studio (Ed25519, одноразовые, привязка к серверу)

## fitintel-pro-deploy@v1.3.1 — 2026-09-27 (архивная запись, не для установки)
- Архив: fitintel-pro-deploy_v1.3.1.zip (контрольная сумма не сохранена; релиз заменён v1.5.2)