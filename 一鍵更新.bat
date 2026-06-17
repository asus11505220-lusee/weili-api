@echo off
chcp 65001 >nul
cd /d "%~dp0"
color 0A
git config core.quotepath false >nul 2>&1

git status -s
echo.
set /p confirm=Upload changes? y/n : 
if /i "%confirm%" neq "y" goto :cancel

git add -A >nul 2>&1

:: 把CSV從這次的commit中移除（不上傳CSV，交給爬蟲管理）
git reset HEAD 今彩539_歷史資料.csv >nul 2>&1
git reset HEAD 威力彩_歷史資料.csv >nul 2>&1

git commit -m "Manual sync update" >nul 2>&1
git pull --rebase >nul 2>&1
git push >temp_push_log.txt 2>&1

set RESULT=FAIL
findstr /C:"main -> main" temp_push_log.txt >nul
if %errorlevel%==0 set RESULT=SUCCESS
findstr /C:"up-to-date" temp_push_log.txt >nul
if %errorlevel%==0 set RESULT=SUCCESS

echo.
echo ===========================
if "%RESULT%"=="SUCCESS" (
    echo Result: Upload Success
) else (
    echo Result: Upload Failed
    type temp_push_log.txt
)
echo ===========================
del temp_push_log.txt >nul 2>&1
pause
goto :end

:cancel
echo Cancelled
pause

:end
