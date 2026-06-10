#!/usr/bin/env python3
"""
RAG 知识库 - 启动入口
首次运行: python run.py init
日常启动: python run.py web
"""

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))


def cmd_init():
    """初始化数据库"""
    from app.database import init_db
    from app.config import settings

    print(f"初始化数据库: {settings.DATABASE_URL}")
    init_db()
    print("完成！")


def cmd_web():
    """启动 Web 界面"""
    import subprocess
    from app.config import settings

    cmd = [
        "streamlit", "run", "app/web/ui.py",
        f"--server.port={settings.STREAMLIT_PORT}",
        f"--server.address={settings.STREAMLIT_SERVER_ADDRESS}",
    ]
    print(f"启动 Web 界面: http://localhost:{settings.STREAMLIT_PORT}")
    subprocess.run(cmd)


def cmd_ingest():
    """导入文档"""
    from app.rag.ingest import ingest_documents

    count = ingest_documents(overwrite=True)
    if count > 0:
        print(f"导入完成: {count} 个向量")
    else:
        print("没有可导入的文档")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python run.py [init|web|ingest]")
        sys.exit(1)

    command = sys.argv[1]
    handlers = {
        "init": cmd_init,
        "web": cmd_web,
        "ingest": cmd_ingest,
    }

    if command in handlers:
        handlers[command]()
    else:
        print(f"未知命令: {command}")
        print("可用命令: init, web, ingest")
