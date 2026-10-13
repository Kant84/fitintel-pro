#define MyAppVersion "1.6.1"

[Setup]
AppName=FitIntel Pro Desktop
AppVersion={#MyAppVersion}
AppPublisher=FitIntel Systems
SetupIconFile=assets\FitIntel_icon.ico
UninstallDisplayIcon={app}\FitIntelDesktop.exe
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

[Files]
Source: "dist\FitIntelDesktop.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\FitIntel Desktop"; Filename: "{app}\FitIntelDesktop.exe"; IconFilename: "{app}\FitIntelDesktop.exe"
Name: "{autodesktop}\FitIntel Desktop"; Filename: "{app}\FitIntelDesktop.exe"; IconFilename: "{app}\FitIntelDesktop.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Создать ярлык на рабочем столе"; GroupDescription: "Дополнительные задачи:"

[Run]
Filename: "{app}\FitIntelDesktop.exe"; Description: "Запустить FitIntel Desktop"; Flags: postinstall skipifsilent