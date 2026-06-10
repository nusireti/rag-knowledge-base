"""
用户会话状态管理
管理 Streamlit 中的登录状态、当前知识库、当前对话
"""

from __future__ import annotations

from typing import Optional

import streamlit as st

from app.auth import validate_session, get_user_by_id
from app.models import User


def get_current_user() -> Optional[User]:
    """从 session_state 获取当前登录用户"""
    token = st.session_state.get("auth_token")
    if not token:
        return None

    user_id = validate_session(token)
    if not user_id:
        clear_auth()
        return None

    return get_user_by_id(user_id)


def is_authenticated() -> bool:
    """检查用户是否已登录"""
    return get_current_user() is not None


def set_auth(token: str):
    """保存认证 token"""
    st.session_state["auth_token"] = token
    # 更新用户信息
    user_id = validate_session(token)
    if user_id:
        user = get_user_by_id(user_id)
        if user:
            st.session_state["user_id"] = user.id
            st.session_state["username"] = user.username
            st.session_state["display_name"] = user.display_name


def clear_auth():
    """清除登录状态"""
    for key in ["auth_token", "user_id", "username", "display_name"]:
        st.session_state.pop(key, None)


def require_auth():
    """要求用户登录，未登录则显示登录页面"""
    if not is_authenticated():
        st.warning("请先登录")
        st.stop()
