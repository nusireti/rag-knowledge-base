# =============================================
# RAG Knowledge Base - 生产级 Docker 镜像
# 多阶段构建：最小化最终镜像体积
# =============================================

# ---- 构建阶段 ----
FROM python:3.11-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# ---- 运行阶段 ----
FROM python:3.11-slim

WORKDIR /app

# 最小运行时依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 复制 Python 依赖
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# 复制应用代码
COPY . .

# 入口脚本
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# 创建数据目录
RUN mkdir -p /app/data && chmod 755 /app/data

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -sf http://localhost:8501/ || exit 1

EXPOSE 8501

ENTRYPOINT ["/entrypoint.sh"]
