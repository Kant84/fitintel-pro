@echo off
chcp 65001 >nul
title FitIntel Pro - Klients
set "SERVER=%~1"
set "SETUP=%~dp0FitIntelDesktop-Setup_v1.6.1.exe"
set "EXE=%LOCALAPPDATA%\Programs\FitIntel Desktop\FitIntelDesktop.exe"

if not exist "%EXE%" (
    if exist "%SETUP%" (
        echo Installing FitIntel client...
        start "" /wait "%SETUP%" /VERYSILENT /SUPPRESSMSGBOXES /NORESTART
    ) else (
        echo Installer not found: %SETUP%
        pause
        exit /b 1
    )
)

set "LNK=%USERPROFILE%\Desktop\FitIntel Pro.lnk"
if not exist "%LNK%" (
    powershell -NoProfile -Command "$s=(New-Object -COM WScript.Shell).CreateShortcut('%LNK%');$s.TargetPath='%~f0';$s.WorkingDirectory='%~dp0';$s.IconLocation='%EXE%,0';$s.Save()"
)

if not "%SERVER%"=="" (
    start "" "%EXE%" --server %SERVER%
) else (
    start "" "%EXE%"
)
