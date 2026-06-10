"""认证模块测试"""

from app.auth import (
    hash_password, verify_password,
    create_session, validate_session,
    create_user, authenticate_user,
)
from app.database import get_db
from app.models import User


class TestPasswordHashing:
    def test_hash_and_verify(self):
        h = hash_password("hello123")
        assert verify_password("hello123", h)
        assert not verify_password("wrong", h)

    def test_different_hashes(self):
        h1 = hash_password("same")
        h2 = hash_password("same")
        assert h1 != h2  # bcrypt uses random salt


class TestSessionTokens:
    def test_create_and_validate(self):
        token = create_session("user_123")
        uid = validate_session(token)
        assert uid == "user_123"

    def test_invalid_token(self):
        assert validate_session("invalid.token.here") is None
        assert validate_session("") is None
        assert validate_session("a.b.c.d") is None


class TestUserCreation:
    def test_create_user(self, setup_db):
        user = create_user("newuser", "password123")
        assert user is not None
        assert user.username == "newuser"

    def test_duplicate_username(self, setup_db):
        create_user("dupuser", "password123")
        user2 = create_user("dupuser", "otherpass")
        assert user2 is None

    def test_authenticate(self, setup_db):
        create_user("authuser", "secret123")
        user = authenticate_user("authuser", "secret123")
        assert user is not None
        assert user.username == "authuser"

        wrong = authenticate_user("authuser", "wrongpass")
        assert wrong is None

    def test_short_password(self, setup_db):
        user = create_user("testuser", "12345")
        assert user is None
