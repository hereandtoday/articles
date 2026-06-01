@echo off
cd /d "%~dp0"
start http://localhost:8080
echo 浏览器已打开: http://localhost:8080
echo 按 Ctrl+C 停止服务
python -m http.server 8080
pause
