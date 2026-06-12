@echo off
REM ===== 一键推送到 GitHub（需先安装 GitHub CLI: https://cli.github.com） =====
REM 用法：双击运行，或在本目录命令行执行 push_to_github.bat
chcp 65001 >nul
echo.
echo 正在检查 GitHub CLI 登录状态...
gh auth status >nul 2>&1
if errorlevel 1 (
  echo 未登录，开始登录（浏览器会打开，按提示授权）...
  gh auth login
)
echo.
set /p REPO="给仓库起个名字（如 daily-brief）: "
echo 正在创建仓库并推送...
gh repo create %REPO% --private --source=. --remote=origin --push
echo.
echo 完成！接下来在浏览器打开该仓库，按 README 的"方式二"开启 Pages 即可。
pause
