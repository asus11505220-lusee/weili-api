@echo off
chcp 65001 >nul
cd /d "%~dp0"
color 0A
git config core.quotepath false >nul 2>&1

cls
echo ===================================================
echo   GitHub 全檔案一鍵同步系統
echo ===================================================
echo.
echo [第一步] 掃描目前所有變動的檔案：
echo ---------------------------------------------------
git status -s
echo ---------------------------------------------------
echo.

set /p confirm=是否確認上傳以上變動的檔案？ y/n : 
if /i "%confirm%" neq "y" goto :cancel

git add -A >nul 2>&1
git commit -m "手動全端同步：更新所有檔案與程式腳本" >nul 2>&1
git pull --rebase >nul 2>&1
git push >temp_push_log.txt 2>&1
type temp_push_log.txt | findstr /C:"main -> main" >nul
if %errorlevel%==0 (
    set RESULT=SUCCESS
) else (
    set RESULT=FAIL
)

cls
echo ===================================================
echo            執行結果
echo ===================================================
echo.
if "%RESULT%"=="SUCCESS" (
    echo   狀態：上傳成功
    echo   檔案已同步到 GitHub
) else (
    echo   狀態：上傳失敗
    echo   詳細錯誤如下：
    echo ---------------------------------------------------
    type temp_push_log.txt
    echo ---------------------------------------------------
)
echo.
echo ===================================================
del temp_push_log.txt >nul 2>&1
pause
goto :end

:cancel
cls
echo 已取消上傳，未進行任何變動。
pause

:end
