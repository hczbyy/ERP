@echo off
chcp 65001 >nul
echo 正在启动 Redis（D:\springboot依赖\redis）...
start "OpenERP Redis" /D "D:\springboot依赖\redis" "D:\springboot依赖\redis\redis-server.exe" redis.conf
timeout /t 2 >nul
echo Redis 已启动（端口 6379）。关闭本窗口不会影响 Redis。
pause
