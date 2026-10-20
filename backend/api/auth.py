"""
认证 API: 登录、注册、验证码
"""

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, EmailStr, Field

from app.auth import (
    authenticate_user,
    create_session,
    create_user,
    get_user_by_email,
    get_user_by_username,
    validate_password,
)
from app.database import init_db

router = APIRouter()

# 确保数据库已初始化
init_db()


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=32)
    password: str = Field(..., min_length=1, max_length=128)


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=2, max_length=32)
    password: str = Field(..., min_length=6, max_length=128)
    email: str = ""
    verify_code: str = ""


class VerifyCodeRequest(BaseModel):
    email: str = Field(..., max_length=128)


class TokenResponse(BaseModel):
    token: str
    user_id: str
    username: str
    display_name: str


@router.post("/login")
async def login(req: LoginRequest):
    """用户登录"""
    user = authenticate_user(req.username, req.password)
    if not user:
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    token = create_session(user.id)
    return TokenResponse(
        token=token,
        user_id=user.id,
        username=user.username,
        display_name=user.display_name or user.username,
    )


@router.get("/capabilities")
async def auth_capabilities():
    """前端用来判断是否展示邮箱验证流程。"""
    from app.verify import email_verification_enabled

    return {"email_verification": email_verification_enabled()}


@router.post("/register")
async def register(req: RegisterRequest):
    """用户注册（校验顺序：输入 → 唯一性 → 验证码）。"""
    from app.verify import email_verification_enabled, verify_code

    username = req.username.strip()

    # ---- 输入合法性 ----
    if not (2 <= len(username) <= 32):
        raise HTTPException(status_code=400, detail="用户名长度需在 2-32 个字符之间")
    if not username.replace("_", "").replace("-", "").isalnum():
        raise HTTPException(
            status_code=400,
            detail="用户名只能包含字母、数字、下划线和短横线",
        )

    valid, msg = validate_password(req.password)
    if not valid:
        raise HTTPException(status_code=400, detail=msg)

    email = req.email.strip()
    if email and ("@" not in email or "." not in email):
        raise HTTPException(status_code=400, detail="邮箱格式不正确")

    # ---- 唯一性 ----
    if get_user_by_username(username):
        raise HTTPException(status_code=409, detail="用户名已被注册")

    if email and get_user_by_email(email):
        raise HTTPException(
            status_code=409,
            detail="该邮箱已被注册，请换一个邮箱或留空",
        )

    # ---- 验证码（仅邮件服务可用且填了邮箱时） ----
    if email and email_verification_enabled():
        if not verify_code(email, req.verify_code):
            raise HTTPException(status_code=400, detail="验证码错误或已过期")

    user = create_user(username, req.password, email=email)
    if not user:
        raise HTTPException(status_code=400, detail="注册失败，请检查信息")

    token = create_session(user.id)
    return TokenResponse(
        token=token,
        user_id=user.id,
        username=user.username,
        display_name=user.display_name or user.username,
    )


@router.post("/verify-code")
async def send_verify_code(req: VerifyCodeRequest):
    """发送邮箱验证码（未配置 SMTP 时明确告知，而不是 500）"""
    from app.verify import email_verification_enabled, send_verify_code as _send

    if not email_verification_enabled():
        raise HTTPException(
            status_code=503,
            detail="邮件服务未配置，注册时可直接留空邮箱",
        )

    ok = _send(req.email)
    if not ok:
        raise HTTPException(status_code=500, detail="验证码发送失败")
    return {"message": "验证码已发送"}


@router.get("/me")
async def get_current_user(authorization: str = Header(""), token: str = ""):
    """获取当前用户信息（兼容 Bearer header 与 ?token= 查询参数）"""
    from app.auth import validate_session, get_user_by_id

    raw_token = token
    if not raw_token and authorization.startswith("Bearer "):
        raw_token = authorization[7:]
    if not raw_token:
        raise HTTPException(status_code=401, detail="未登录")

    user_id = validate_session(raw_token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Token 无效或已过期")
    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return {
        "user_id": user.id,
        "username": user.username,
        "display_name": user.display_name or user.username,
        "email": user.email or "",
        "is_admin": user.is_admin,
        "created_at": user.created_at.isoformat() if user.created_at else "",
    }
