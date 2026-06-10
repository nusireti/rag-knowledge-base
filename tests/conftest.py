"""测试配置和夹具"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from app.database import init_db, drop_db, get_db
from app.auth import hash_password
from app.models import User, KnowledgeBase


@pytest.fixture(autouse=True)
def setup_db():
    """每个测试前重建数据库"""
    init_db()
    yield
    drop_db()


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
def test_kb(test_user):
    """创建测试知识库"""
    with get_db() as db:
        kb = KnowledgeBase(
            name="test-kb",
            display_name="测试知识库",
            owner_id=test_user.id,
        )
        db.add(kb)
        db.flush()
        yield kb
