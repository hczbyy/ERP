@echo off
chcp 65001 >nul
cd /d %~dp0
echo ============================================
echo   OpenERP 一键启动
echo   启动后浏览器访问 http://127.0.0.1:8000
echo   关闭本窗口即停止服务
echo ============================================
python run.py
pause