@echo off
chcp 65001 >nul
title RAG 知识库 - 安装启动脚本
echo ========================================
echo   🧠 RAG 知识库 - 一键安装启动
echo ========================================
echo.
echo [1/3] 安装 Python 依赖...
pip install -r requirements.txt
if %ERRORLEVEL% NEQ 0 (
    echo ❌ 安装失败，请检查 Python 和 pip 是否正确安装
    pause
    exit /b 1
)
echo.
echo [2/3] 确保文档目录存在...
if not exist documents\ (
    mkdir documents
    echo ✅ 已创建 documents/ 目录
)
echo.
echo [3/3] 启动 Web 界面...
echo.
echo ========================================
echo ✅ 安装完成！
echo.
echo 使用说明：
echo   1. 把 PDF/TXT/MD 文件放到 documents/ 目录
echo   2. 启动 Streamlit：
echo.
echo      streamlit run app.py
echo.
echo   3. 浏览器打开 http://localhost:8501
echo   4. 点击左侧「刷新知识库」按钮
echo   5. 开始提问！
echo.
echo 首次启动会下载 AI 模型（约 100MB），请耐心等待
echo ========================================
pause
