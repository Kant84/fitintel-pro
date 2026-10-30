; ── Шапка: все define ────────────────────────────────
#define MyAppName "FitIntel Pro Desktop"
#define MyAppVersion "1.6.1"
#define MyAppPublisher "FitIntel Systems"
#define MyAppExeName "FitIntelDesktop.exe"
#define MyDefaultApiBase "http://localhost/api/v1"

; ── Секция [Setup] ──────────────────────────────────
[Setup]
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
SetupIconFile=assets\FitIntel_icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
DefaultDirName={autopf}\FitIntel Desktop
DefaultGroupName=FitIntel Pro
OutputDir=installer_out
OutputBaseFilename=FitIntelDesktop-Setup_v{#MyAppVersion}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=lowest

; ── Языки ───────────────────────────────────────────
[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"

; ── Файлы ───────────────────────────────────────────
[Files]
Source: "dist\FitIntelDesktop\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs
; mpv, tools\nssm.exe, assets, scripts\music — уже внутри exe (onefile),
; поэтому отдельно копировать НЕ НУЖНО.

; ── Ярлыки ──────────────────────────────────────────
[Icons]
Name: "{group}\FitIntel Desktop";       Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\FitIntel Desktop"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

; ── Доп. задачи ─────────────────────────────────────
[Tasks]
Name: "desktopicon"; Description: "Создать ярлык на рабочем столе"; GroupDescription: "Дополнительные задачи:"

; ── Запуск после установки ──────────────────────────
[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Запустить FitIntel Desktop"; Flags: postinstall skipifsilent

; ── Диалог с URL сервера ────────────────────────────
[Code]
var
  LicensePage: TInputQueryWizardPage;
  ServerPage: TInputQueryWizardPage;

procedure InitializeWizard();
begin
  LicensePage := CreateInputQueryPage(wpSelectDir,
    'Лицензия клуба',
    'Введите лицензионный ключ',
    'Ключ формата FIPRO-... выдаётся в License Studio. ' +
    'Логин главного администратора и временный пароль ' +
    'содержатся в самом ключе — отдельно вводить их не нужно.');
  LicensePage.Add('Лицензионный ключ:', False);
  LicensePage.Values[0] := '';

  ServerPage := CreateInputQueryPage(LicensePage.ID,
    'Адрес сервера клуба',
    'Укажите адрес API-сервера FitIntel',
    'Введите адрес сервера клуба (выдаётся поставщиком системы). ' +
    'Примеры:' + #13#10 +
    '  - Облачный сервер: https://club-xxx.fitintel.ru/api/v1' + #13#10 +
    '  - Локальный сервер: http://192.168.1.100/api/v1' + #13#10 +
    '  - Удалённый по VPN: http://10.8.0.5:8001/api/v1');
  ServerPage.Add('Адрес API:', False);
  ServerPage.Values[0] := '{#MyDefaultApiBase}';
end;

function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;
  if CurPageID = LicensePage.ID then
  begin
    if (Trim(LicensePage.Values[0]) <> '') and
       (Copy(Trim(LicensePage.Values[0]), 1, 6) <> 'FIPRO-') then
    begin
      MsgBox('Ключ должен начинаться с FIPRO-. Оставьте поле пустым, если лицензия уже активирована.', mbError, MB_OK);
      Result := False;
      Exit;
    end;
  end;
  if CurPageID = ServerPage.ID then
  begin
    if Trim(ServerPage.Values[0]) = '' then
    begin
      MsgBox('Укажите адрес сервера клуба.', mbError, MB_OK);
      Result := False;
      Exit;
    end;
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  JsonFile, JsonStr, ApiBase, LicenseKey: String;
begin
  if CurStep = ssPostInstall then
  begin
    ApiBase := Trim(ServerPage.Values[0]);
    LicenseKey := Trim(LicensePage.Values[0]);
    StringChangeEx(LicenseKey, '\', '\\', True);
    StringChangeEx(LicenseKey, '"', '\"', True);
    StringChangeEx(ApiBase, '\', '\\', True);
    StringChangeEx(ApiBase, '"', '\"', True);

    JsonFile := ExpandConstant('{app}\client_settings.json');
    JsonStr :=
      '{' + #13#10 +
      '  "api_base": "' + ApiBase + '",' + #13#10 +
      '  "license_key": "' + LicenseKey + '",' + #13#10 +
      '  "theme": "dark",' + #13#10 +
      '  "dj_agent": {' + #13#10 +
      '    "token": "",' + #13#10 +
      '    "lib": "",' + #13#10 +
      '    "mic": false' + #13#10 +
      '  }' + #13#10 +
      '}';

    // Повторная установка явно перенастраивает сервер. Не сохраняем
    // авторизацию прежнего сервера в конфигурации нового подключения.
    if not SaveStringToFile(JsonFile, JsonStr, False) then
      RaiseException('Не удалось сохранить адрес сервера в client_settings.json');

    // connections.json: единственный профиль с введённым сервером.
    // Иначе stale-профиль переживёт переустановку и авто-подключение
    // перекроет api_base старым адресом.
    JsonFile := ExpandConstant('{app}\connections.json');
    JsonStr :=
      '[' + #13#10 +
      '  {' + #13#10 +
      '    "name": "Сервер клуба",' + #13#10 +
      '    "type": "web",' + #13#10 +
      '    "local_path": "",' + #13#10 +
      '    "web_url": "' + ApiBase + '",' + #13#10 +
      '    "web_login": "",' + #13#10 +
      '    "web_pass": "",' + #13#10 +
      '    "db_host": "",' + #13#10 +
      '    "db_port": "",' + #13#10 +
      '    "db_name": "",' + #13#10 +
      '    "db_user": "",' + #13#10 +
      '    "db_pass": ""' + #13#10 +
      '  }' + #13#10 +
      ']';
    if not SaveStringToFile(JsonFile, JsonStr, False) then
      RaiseException('Не удалось сохранить connections.json');
  end;
end;