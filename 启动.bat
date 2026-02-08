@echo off
chcp 65001 >nul 2>&1
title AI API 密钥测试工具

echo.
echo   ==========================================
echo     AI API 密钥全能测试工具 - 启动中...
echo   ==========================================
echo.

:: 检查 Python 是否安装
where py >nul 2>&1
if %errorlevel%==0 (
    set PYTHON=py
    goto :found
)
where python >nul 2>&1
if %errorlevel%==0 (
    set PYTHON=python
    goto :found
)

echo   [错误] 未检测到 Python，请先安装 Python 3.8+
echo.
echo   下载地址: https://www.python.org/downloads/
echo   安装时请勾选 "Add Python to PATH"
echo.
pause
exit /b 1

:found
echo   [√] 已检测到 Python: %PYTHON%

:: 检查并安装依赖
%PYTHON% -c "import requests" >nul 2>&1
if %errorlevel% neq 0 (
    echo   [*] 正在安装依赖...
    %PYTHON% -m pip install -r requirements.txt -q
    echo   [√] 依赖安装完成
) else (
    echo   [√] 依赖已就绪
)

echo.
echo   [*] 正在启动 Web 服务...
echo   [*] 浏览器将自动打开，请稍候...
echo.

:: 启动 Web 服务
%PYTHON% gemini_test.py --web
