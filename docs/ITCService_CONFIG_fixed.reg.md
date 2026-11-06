[HKEY_LOCAL_MACHINE\SOFTWARE\ITCService]

"CheckAccessURL"="http://192.168.1.50:8001/api/v1/skud/checkaccess"

"EventURL"="http://192.168.1.50:8001/api/v1/skud/event"

"HealthCheckURL"="http://192.168.1.50:8001/api/v1/skud/health_check"

"BasicAuthUser"="itc"

"BasicAuthPass"=<ITC_BASIC_PASSWORD из deploy/.env — вписать вручную>

"TimeoutMs"=dword:00001388
