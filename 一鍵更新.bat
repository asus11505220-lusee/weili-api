@echo off
chcp 65001 >nul
cd /d "%~dp0"
color 0A
git config core.quotepath false >nul 2>&1

git status -s
echo.
set /p confirm=上傳以上變動的檔案? y/n : 
if /i "%confirm%" neq "y" goto :cancel

git add -A >nul 2>&1
git commit -m "手動全端同步：更新所有檔案與程式腳本" >nul 2>&1
git pull --rebase >nul 2>&1
git push >temp_push_log.txt 2>&1

findstr /C:"main -> main" temp_push_log.txt >nul
if %errorlevel%==0 set RESULT=SUCCESS

findstr /C:"up-to-date" temp_push_log.txt >nul
if %errorlevel%==0 set RESULT=SUCCESS

echo.
echo ===========================
if "%RESULT%"=="SUCCESS" (
    echo 結果：上傳成功
) else (
    echo 結果：上傳失敗，詳細訊息：
    type temp_push_log.txt
)
echo ===========================
del temp_push_log.txt >nul 2>&1
pause
goto :end

:cancel
echo 已取消
pause

:end
