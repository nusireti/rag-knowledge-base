#!/bin/bash
# =============================================
# RAG Knowledge Base - Docker 入口脚本
# =============================================
set -e

# 生成默认 .env（如果不存在）
if [ ! -f /app/.env ]; then
    cat > /app/.env << EOF
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
DEBUG=false
OLLAMA_BASE_URL=http://ollama:11434
OLLAMA_MODEL=qwen2.5:3b
EMBEDDING_PROVIDER=local
LLM_PROVIDER=local
EOF
    echo "已生成默认 .env 文件"
fi

# 等待 Ollama 就绪
echo "等待 Ollama 服务..."
until curl -sf http://ollama:11434/api/tags > /dev/null 2>&1; do
    sleep 2
done
echo "Ollama 就绪"

# 初始化数据库
python3 -c "from app.database import init_db; init_db()" 2>/dev/null || true

# 启动应用
exec streamlit run app/web/ui.py \
    --server.port=${STREAMLIT_PORT:-8501} \
    --server.address=0.0.0.0 \
    --server.headless=true \
    --browser.gatherUsageStats=false
