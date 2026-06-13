@echo off
chcp 65001 >nul
cd /d "%~dp0"
color 0A

git config core.quotepath false

echo ===================================================
echo   GitHub 全檔案一鍵同步系統
echo ===================================================
echo.
echo [第一步] 掃描目前所有變動的檔案：
echo ---------------------------------------------------
git status -s
echo ---------------------------------------------------
echo.

set /p confirm=是否確認上傳以上變動的檔案？ (y/n): 
if /i "%confirm%" neq "y" goto :cancel

echo.
echo [第二步] 儲存修改...
git add -A
git commit -m "手動全端同步：更新所有檔案與程式腳本"

echo.
echo [第三步] 同步GitHub最新版本...
git pull --rebase

echo.
echo [第四步] 上傳到GitHub...
git push

echo.
echo ===================================================
echo   流程結束，請查看上方訊息確認是否成功。
echo   (看到 To https://github.com/... 代表上傳成功)
echo ===================================================
pause
goto :end

:cancel
echo.
echo 已取消上傳，未進行任何變動。
pause

:end
