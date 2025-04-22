@echo off
REM 启动前端
start "Frontend" cmd /k "cd frontend && npm run dev"

REM 启动后端（激活虚拟环境）
start "Backend" cmd /k "cd backend && call venv\Scripts\activate.bat && python main.py"