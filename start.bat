@echo off
REM Page Assist Python Edition - Windows启动脚本

echo ======================================
echo    Page Assist - Python Edition
echo ======================================
echo.

REM 检查Python
python --version >nul 2>&1
if errorlevel 1 (
    echo 错误: 未找到Python，请先安装Python
    pause
    exit /b 1
)

REM 检查依赖
python -c "import streamlit" >nul 2>&1
if errorlevel 1 (
    echo 正在安装依赖...
    pip install -r requirements.txt
)

REM 解析参数
set MODE=%1
if "%MODE%"=="" set MODE=streamlit

if "%MODE%"=="streamlit" goto :streamlit
if "%MODE%"=="web" goto :streamlit
if "%MODE%"=="ui" goto :streamlit
if "%MODE%"=="api" goto :api
if "%MODE%"=="server" goto :api
if "%MODE%"=="backend" goto :api
if "%MODE%"=="init" goto :init
if "%MODE%"=="both" goto :both
if "%MODE%"=="help" goto :help
goto :help

:streamlit
echo 启动 Streamlit 前端...
echo 访问地址: http://localhost:8501
python -m streamlit run app.py --server.port 8501
goto :end

:api
echo 启动 API 服务器...
echo API地址: http://localhost:8000
python -m uvicorn api:app --host 0.0.0.0 --port 8000 --reload
goto :end

:init
echo 初始化数据库...
python main.py --mode init
goto :end

:both
echo 启动前端和API服务器...
start "Page Assist API" python -m uvicorn api:app --host 0.0.0.0 --port 8000 --reload
timeout /t 2 /nobreak >nul
python -m streamlit run pages\主页.py --server.port 8501
goto :end

:help
echo 使用方法: %0 [模式]
echo.
echo 模式选项:
echo   streamlit  (默认) - 启动Streamlit前端
echo   api                  - 启动API服务器
echo   both                 - 同时启动前端和API
echo   init                 - 初始化数据库
echo.
echo 示例:
echo   %0                  - 启动前端
echo   %0 api              - 启动API服务器
echo   %0 both             - 启动两个服务
goto :end

:end
pause
