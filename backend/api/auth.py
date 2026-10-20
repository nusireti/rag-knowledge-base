"""
认证 API: 登录、注册、验证码
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr, Field

from app.auth import authenticate_user, create_user, create_session, get_user_by_username
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
    """用户注册（带可选的验证码校验）"""
    from app.verify import email_verification_enabled, verify_code

    # 只有邮件服务真正可用时才强制验证码。
    # 未配置 SMTP 时如果还强制，注册页会永远卡在「验证码发送失败」。
    if req.email and email_verification_enabled():
        if not verify_code(req.email, req.verify_code):
            raise HTTPException(status_code=400, detail="验证码错误或已过期")

    # 检查用户是否已存在
    existing = get_user_by_username(req.username)
    if existing:
        raise HTTPException(status_code=409, detail="用户名已被注册")

    user = create_user(req.username, req.password, email=req.email)
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
async def get_current_user(token: str):
    """根据 Token 获取当前用户信息"""
    from app.auth import validate_session, get_user_by_id
    user_id = validate_session(token)
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
