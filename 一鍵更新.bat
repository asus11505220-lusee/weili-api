@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul
cd /d "%~dp0"
color 0A
git config core.quotepath false >nul 2>&1

cls
echo === 修改的檔案 ===
git status -s
echo ==================
echo.

set "confirm="
set /p confirm=上傳嗎？(y/n): 
if /i not "!confirm!"=="y" goto :cancel

git add -A >nul 2>&1
git commit -m "Manual sync update"
git pull --rebase
echo.
echo （如果上面有 CONFLICT 紅字，截圖給我，先別繼續）
pause

git push
echo.
echo （看到 To https://github.com/... 代表成功）
pause
goto :eof

:cancel
echo 已取消
pause
