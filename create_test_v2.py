# Создаём новый скрипт тестирования
with open('test_feature_flags_v2.ps1', 'w', encoding='utf-8') as f:
    f.write('''
# test_feature_flags_v2.ps1
{
  "login": "my_new_username",
  "password": "TestPass123!"
} = @{ login = "my_new_username"; password = "TestPass123!" } | ConvertTo-Json
@{access_token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI3ZGIwN2E0Yy0wYmY5LTRhNTctYmQ5Zi05ZjA4OGJhMTU3ODMiLCJleHAiOjE3ODE4NzUxMTQsInRva2VuX3R5cGUiOiJhY2Nlc3MifQ.vZu6JeWj31ZYQIFGeuNvb3_8uL2-ll51-sezTkHuXyY; token_type=bearer; expires_in=1800} = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/auth/login" -Method POST -Body {
  "login": "my_new_username",
  "password": "TestPass123!"
} -ContentType "application/json"
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI3ZGIwN2E0Yy0wYmY5LTRhNTctYmQ5Zi05ZjA4OGJhMTU3ODMiLCJleHAiOjE3ODE4NzUxMTQsInRva2VuX3R5cGUiOiJhY2Nlc3MifQ.vZu6JeWj31ZYQIFGeuNvb3_8uL2-ll51-sezTkHuXyY = @{access_token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI3ZGIwN2E0Yy0wYmY5LTRhNTctYmQ5Zi05ZjA4OGJhMTU3ODMiLCJleHAiOjE3ODE4NzUxMTQsInRva2VuX3R5cGUiOiJhY2Nlc3MifQ.vZu6JeWj31ZYQIFGeuNvb3_8uL2-ll51-sezTkHuXyY; token_type=bearer; expires_in=1800}.access_token

System.Collections.Hashtable = @{
    "Authorization" = "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI3ZGIwN2E0Yy0wYmY5LTRhNTctYmQ5Zi05ZjA4OGJhMTU3ODMiLCJleHAiOjE3ODE4NzUxMTQsInRva2VuX3R5cGUiOiJhY2Nlc3MifQ.vZu6JeWj31ZYQIFGeuNvb3_8uL2-ll51-sezTkHuXyY"
    "Content-Type" = "application/json"
}

Write-Host "=== E7a.1 Создание флага (positive) ==="
{
  "default_value": "true",
  "flag_key": "test_debug",
  "flag_type": "boolean"
} = @{
    name = "Test Flag"
    flag_key = "test_flag_399622325"
    flag_type = "boolean"
    default_value = "true"
    description = "Test flag"
} | ConvertTo-Json
 = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/feature-flags" -Method POST -Headers System.Collections.Hashtable -Body {
  "default_value": "true",
  "flag_key": "test_debug",
  "flag_type": "boolean"
}
 = .flag_key
Write-Host "Created flag: "

Write-Host "
=== E7a.3 Создание дублирующего (negative) ==="
 = @{
    name = "Test Flag 2"
    flag_key = 
    flag_type = "boolean"
    default_value = "false"
} | ConvertTo-Json
Invoke-RestMethod -Uri "http://localhost:8001/api/v1/feature-flags" -Method POST -Headers System.Collections.Hashtable -Body 

Write-Host "
=== E7a.4 Проверка флага (positive) ==="
{
  "default_value": "true",
  "flag_key": "test_debug",
  "flag_type": "boolean"
} = @{
    flag_key = 
    client_id = "966e13cd-e38b-4641-804e-f69942ccd7dc"
} | ConvertTo-Json
Invoke-RestMethod -Uri "http://localhost:8001/api/v1/feature-flags/check" -Method POST -Headers System.Collections.Hashtable -Body {
  "default_value": "true",
  "flag_key": "test_debug",
  "flag_type": "boolean"
}

Write-Host "
=== E7a.5 Проверка несуществующего (negative) ==="
{
  "default_value": "true",
  "flag_key": "test_debug",
  "flag_type": "boolean"
} = @{
    flag_key = "nonexistent_flag_12345"
    client_id = "966e13cd-e38b-4641-804e-f69942ccd7dc"
} | ConvertTo-Json
Invoke-RestMethod -Uri "http://localhost:8001/api/v1/feature-flags/check" -Method POST -Headers System.Collections.Hashtable -Body {
  "default_value": "true",
  "flag_key": "test_debug",
  "flag_type": "boolean"
}

Write-Host "
=== E7a.14 Недопустимый тип (negative) ==="
{
  "default_value": "true",
  "flag_key": "test_debug",
  "flag_type": "boolean"
} = @{
    name = "Invalid Flag"
    flag_key = "invalid_type_flag"
    flag_type = "invalid"
    default_value = "true"
} | ConvertTo-Json
Invoke-RestMethod -Uri "http://localhost:8001/api/v1/feature-flags" -Method POST -Headers System.Collections.Hashtable -Body {
  "default_value": "true",
  "flag_key": "test_debug",
  "flag_type": "boolean"
}

Write-Host "
=== E7a.15 Удаление флага (positive) ==="
Invoke-RestMethod -Uri "http://localhost:8001/api/v1/feature-flags/" -Method DELETE -Headers System.Collections.Hashtable

Write-Host "
=== Готово! ==="
''')

print("test_feature_flags_v2.ps1 создан!")
