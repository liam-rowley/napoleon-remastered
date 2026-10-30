@echo off
rem purpose: build the self-contained GPU environment for the UI art upscaler in <work>\art_build (embeddable Python, torch cu130, spandrel, pinned models); nothing system-wide
rem usage: upscale\pc\setup_env.cmd [work folder, default C:\napoleon_remastered_pc\upscale]   then: <work>\art_build\py\python.exe upscale\pc\env_check.py --models <work>\art_build\models --pins upscale\napoleon\models.json
rem when: first use on a PC, or after deleting art_build; safe to re-run (finished downloads are skipped)
rem not-a-verb: a Windows setup script; `wsc upscale env` runs the check it ends with
setlocal
set "WORK=%~1"
if "%WORK%"=="" set "WORK=C:\napoleon_remastered_pc\upscale"
set "AB=%WORK%\art_build"
set "REPO=%~dp0..\.."
if not exist "%AB%\dl" mkdir "%AB%\dl"
if not exist "%AB%\py" mkdir "%AB%\py"
if not exist "%AB%\models" mkdir "%AB%\models"
if not exist "%AB%\cache\pip" mkdir "%AB%\cache\pip"
if not exist "%AB%\tmp" mkdir "%AB%\tmp"
set "PIP_CACHE_DIR=%AB%\cache\pip"
set "TMP=%AB%\tmp"
set "TEMP=%AB%\tmp"
if not exist "%AB%\dl\python-3.12.10-embed-amd64.zip" curl -sSfL -o "%AB%\dl\python-3.12.10-embed-amd64.zip" https://www.python.org/ftp/python/3.12.10/python-3.12.10-embed-amd64.zip || exit /b 1
if not exist "%AB%\dl\get-pip.py" curl -sSfL -o "%AB%\dl\get-pip.py" https://bootstrap.pypa.io/get-pip.py || exit /b 1
if not exist "%AB%\py\python.exe" "%SystemRoot%\System32\tar.exe" -xf "%AB%\dl\python-3.12.10-embed-amd64.zip" -C "%AB%\py" || exit /b 1
powershell -NoProfile -Command "(Get-Content '%AB%\py\python312._pth') -replace '^#import site','import site' | Set-Content '%AB%\py\python312._pth'"
"%AB%\py\python.exe" -c "import pip" 2>nul || "%AB%\py\python.exe" "%AB%\dl\get-pip.py" --no-warn-script-location || exit /b 1
"%AB%\py\python.exe" -m pip install --no-warn-script-location torch==2.14.1 --index-url https://download.pytorch.org/whl/cu130 || exit /b 1
"%AB%\py\python.exe" -m pip install --no-warn-script-location numpy==2.5.2 pillow==12.3.0 spandrel==0.4.2 || exit /b 1
"%AB%\py\python.exe" "%REPO%\upscale\core\model.py" fetch "%REPO%\upscale\napoleon\models.json" "%AB%\models" || exit /b 1
"%AB%\py\python.exe" "%REPO%\upscale\pc\env_check.py" --models "%AB%\models" --pins "%REPO%\upscale\napoleon\models.json"
