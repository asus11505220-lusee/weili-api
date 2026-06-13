@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul
cd /d "%~dp0"
color 0A

git config core.quotepath false

echo ===================================================
echo   GitHub Sync Tool
echo ===================================================
echo.
echo [Step 1] Checking for local changes...
echo ---------------------------------------------------
git status -s
echo ---------------------------------------------------
echo.

set "confirm="
set /p confirm=Confirm commit and upload these changes? (y/n): 
if /i not "!confirm!"=="y" goto :cancel

echo.
echo [Step 2] Staging and committing local changes first...
git add -A
git commit -m "Manual sync update"
echo ---------------------------------------------------
echo.

echo [Step 3] Pulling latest from remote (rebase)...
git pull --rebase
echo ---------------------------------------------------
echo If there is a CONFLICT message above, please screenshot it and stop here.
echo If no conflict, press any key to continue and push.
pause
echo.

echo [Step 4] Pushing to GitHub...
git push
echo ---------------------------------------------------
echo If it shows "To https://github.com/..." above, it succeeded.
echo ===================================================
echo   Done. Please check the messages above.
echo ===================================================
pause
goto :eof

:cancel
echo.
echo Cancelled, no changes made.
pause
