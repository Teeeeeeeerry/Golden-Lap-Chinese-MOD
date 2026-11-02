@echo off
chcp 65001 >nul
rem install.bat 与 restore.bat 共用：用内置运行环境执行命令，结束后停留，让玩家看到结果。
setlocal
set "DIR=%~dp0"
set "PY=%DIR%runtime\python\python.exe"
if not exist "%PY%" (
  echo 缺少内置运行环境，请重新完整解压发布包后再运行。
  pause
  exit /b 1
)
rem 不让玩家自己装的 Python 及其包混进来
set "PYTHONHOME="
set "PYTHONPATH=%DIR%src"
set "PYTHONNOUSERSITE=1"
set "PYTHONUTF8=1"
"%PY%" -m glzh_windows %1
set "CODE=%ERRORLEVEL%"
echo.
pause
exit /b %CODE%
