@echo off
setlocal enabledelayedexpansion

:: Add Aditya's local nodejs path if present
if exist "C:\Users\ADITYA RAJ\nodejs" set "PATH=C:\Users\ADITYA RAJ\nodejs;%PATH%"
cd /d "%~dp0"

echo ===============================================================================
echo                 RADZERO ORBITAL AI - FIREBASE HOSTING DEPLOYER
echo ===============================================================================
echo.
echo Active Tunnel Backend: https://neil-php-coating-junction.trycloudflare.com
echo Target Firebase Project: radzero
echo Target Domain: https://radzero.web.app / https://radzero.firebaseapp.com
echo.

:: 1. Verify or Sync Static Export directory
if not exist "out" (
    if exist "mission-control\out" (
        echo [*] Syncing mission-control\out to out...
        xcopy /s /e /y /q "mission-control\out" "out\" >nul
    ) else (
        echo [ERROR] No static export folder 'out' found.
        echo Please build the project first:
        echo     cd mission-control
        echo     npm run build
        echo.
        pause
        exit /b 1
    )
)

echo [*] Logging in to Firebase (browser window will open if not logged in)...
call firebase login
echo.
echo [*] Deploying static HUD from out\ to Firebase project: radzero...
call firebase deploy --only hosting

if %errorlevel% equ 0 (
    echo.
    echo ===============================================================================
    echo [SUCCESS] RadZero Web HUD is now LIVE on Firebase Hosting!
    echo.
    echo   Mission Control HUD: https://radzero.web.app
    echo   Backup Mirror:       https://radzero.firebaseapp.com
    echo   Backend Tunnel:      https://neil-php-coating-junction.trycloudflare.com
    echo ===============================================================================
) else (
    echo.
    echo [!] Deployment exited with an issue. If you need to re-authenticate, run:
    echo     call firebase login --reauth
    echo Then run this script again.
)

echo.
pause
