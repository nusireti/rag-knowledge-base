"""测试配置和夹具

⚠️ 隔离原则（重要）
    这里所有的路径都指向临时目录，绝不碰开发数据。

    此前的 conftest 直接用 app.config 的默认 DATABASE_URL，
    而它指向真实的 data/rag.db —— 于是跑一次 pytest 就会把
    开发库里的账号和对话全部删掉（drop_db 是真删表）。
"""

import os
import sys
import tempfile

# === 必须在 import app.* 之前设置 ===
# settings 是模块级单例，一旦被导入就固化了 DATABASE_URL，
# 之后再改环境变量也没用。
_TMP_DIR = os.path.join(tempfile.gettempdir(), "rag_pytest")
os.makedirs(_TMP_DIR, exist_ok=True)
os.environ["DATABASE_URL"] = f"sqlite:///{os.path.join(_TMP_DIR, 'rag_test.db')}"
# 测试里关闭限流：否则同一 TestClient IP 下的批量请求会互相干扰
os.environ["RATE_LIMIT_ENABLED"] = "false"

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from app.config import settings
from app.database import init_db, drop_db, get_db
from app.auth import hash_password
from app.models import User

# 双保险：万一上面的设置失效，这里直接拦下来
_DEV_DB = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "rag.db"))
assert os.path.abspath(_DEV_DB) not in os.path.abspath(settings.DATABASE_URL), (
    "测试连到了开发库！请检查 conftest.py 顶部的 DATABASE_URL 设置"
)


@pytest.fixture(autouse=True)
def setup_db():
    """每个测试前重建测试库（临时文件，不是开发库）"""
    init_db()
    yield
    drop_db()


@pytest.fixture(autouse=True)
def isolate_storage(tmp_path, monkeypatch):
    """
    把知识库目录和对话目录都指向临时目录

    这些模块级常量被各函数在调用时读取，因此在测试期间替换掉即可完全隔离。
    """
    import kb_manager
    import chat_history

    monkeypatch.setattr(kb_manager, "KB_ROOT", str(tmp_path / "knowledge_bases"))
    monkeypatch.setattr(chat_history, "CONVERSATIONS_DIR", str(tmp_path / "conversations"))
    os.makedirs(kb_manager.KB_ROOT, exist_ok=True)
    os.makedirs(chat_history.CONVERSATIONS_DIR, exist_ok=True)
    yield


@pytest.fixture
def test_user():
    """创建测试用户"""
    with get_db() as db:
        user = User(
            username="testuser",
            display_name="Test User",
            password_hash=hash_password("test123456"),
        )
        db.add(user)
        db.flush()
        yield user


@pytest.fixture
def two_users():
    """创建两个用户，用于越权测试"""
    with get_db() as db:
        alice = User(username="alice", display_name="Alice",
                     password_hash=hash_password("alice123456"))
        bob = User(username="bob", display_name="Bob",
                   password_hash=hash_password("bob123456"))
        db.add(alice)
        db.add(bob)
        db.flush()
        yield alice, bob
