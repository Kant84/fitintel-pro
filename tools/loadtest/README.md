Loadtest FitIntel Pro
=====================
1. Данные (nfs):     см. generate_data.py (шапка файла)
2. Прогон (ПК):      pip install locust; $env:FI_TOKEN="..."; locust -f tools/loadtest/locustfile.py --host http://192.168.101.182 --headless -u 100 -r 20 -t 10m --csv loadrun
3. Ресурсы (nfs):    watch -n2 'docker stats --no-stream --format "{{.Name}}: {{.CPUPerc}} {{.MemUsage}}"' deploy-api-1 deploy-db-1
4. Очистка (nfs):    DELETE FROM clients WHERE phone LIKE '+7999LT%';
