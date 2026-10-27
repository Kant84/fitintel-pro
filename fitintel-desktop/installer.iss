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
Source: "dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
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
  ServerPage: TInputQueryWizardPage;

procedure InitializeWizard();
begin
  ServerPage := CreateInputQueryPage(wpSelectDir,
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
  JsonFile, JsonStr, ApiBase: String;
begin
  if CurStep = ssPostInstall then
  begin
    ApiBase := Trim(ServerPage.Values[0]);
    StringChangeEx(ApiBase, '\', '\\', True);
    StringChangeEx(ApiBase, '"', '\"', True);

    JsonFile := ExpandConstant('{app}\client_settings.json');
    JsonStr :=
      '{' + #13#10 +
      '  "api_base": "' + ApiBase + '",' + #13#10 +
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
  end;
end;