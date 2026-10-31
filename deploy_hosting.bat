@echo off
setlocal enabledelayedexpansion

echo ===============================================================================
echo                 RADZERO ORBITAL AI - FIREBASE HOSTING DEPLOYMENT
echo ===============================================================================
echo.
echo Active Tunnel Backend: https://neil-php-coating-junction.trycloudflare.com
echo Target Firebase Project: radzero
echo Target Domain: https://radzero.web.app / https://radzero.firebaseapp.com
echo.

:: 1. Verify Firebase CLI
where firebase >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Firebase CLI was not found in your system PATH.
    echo Please install it globally by running:
    echo     npm install -g firebase-tools
    echo.
    pause
    exit /b 1
)

:: 2. Ensure export directory exists
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

echo [*] Launching Firebase Hosting Deployment...
echo [i] Note: If your browser opens for OAuth login, approve the Google Account permissions.
echo.

firebase deploy --only hosting

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
    echo     firebase login --reauth
    echo Then run this script again.
)

echo.
pause
