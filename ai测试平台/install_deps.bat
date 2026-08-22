@echo off
cd /d "%~dp0"
python -m pip install --target "D:\ai测试平台依赖包" -r "%~dp0requirements.txt"
echo.
echo ==========================================
echo  Install finished. You can start now.
echo ==========================================
pause
