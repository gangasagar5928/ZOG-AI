@echo off
set "PATH=C:\Users\ADITYA RAJ\nodejs;%PATH%"
cd /d "C:\Users\ADITYA RAJ\ZOG-AI"
echo =========================================================
echo   RadZero Mission Control - Firebase Hosting Deployer
echo =========================================================
echo.
echo Logging in to Firebase (browser window will open if not logged in)...
call firebase login
echo.
echo Deploying static HUD from out\ to Firebase project: radzero...
call firebase deploy --only hosting
echo.
echo =========================================================
echo Deployment complete!
echo =========================================================
pause
