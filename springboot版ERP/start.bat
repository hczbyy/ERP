@echo off
chcp 65001 >nul
setlocal

set JAVA_HOME=D:\jdk21
set MAVEN_HOME=D:\springboot依赖\maven\apache-maven-3.9.9
set PATH=%JAVA_HOME%\bin;%MAVEN_HOME%\bin;%PATH%

echo ============================================
echo   OpenERP 企业资源管理系统 (Spring Boot)
echo   JDK21 + Maven + MySQL + Redis
echo ============================================
echo.

echo [1/3] 检查 Redis 是否已启动 ...
D:\springboot依赖\redis\redis-cli.exe -h 127.0.0.1 -p 6379 ping >nul 2>&1
if errorlevel 1 (
  echo Redis 未启动，先帮你启动 Redis ...
  start "OpenERP Redis" /D "D:\springboot依赖\redis" "D:\springboot依赖\redis\redis-server.exe" redis.conf
  timeout /t 3 >nul
) else (
  echo Redis 运行中。
)

echo.
echo [2/3] 编译并启动后端（首次运行需下载依赖，请耐心等待）...
cd /d D:\springboot
call mvn.cmd -DskipTests spring-boot:run

echo.
echo [3/3] 启动完成，浏览器访问 http://127.0.0.1:8080
echo 演示账号 admin / admin123
pause
