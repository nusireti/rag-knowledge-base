"""
模型 API: 获取可用模型列表
"""

from fastapi import APIRouter, Header

from app.auth import validate_session

router = APIRouter()


@router.get("/")
async def get_models(authorization: str = Header(...)):
    """获取可用模型列表"""
    _require_user(authorization)
    # 这里可以扩展为动态获取可用模型
    models = [
        {"id": "local", "name": "Ollama 本地模型", "provider": "local"},
        {"id": "openai", "name": "OpenAI GPT", "provider": "openai"},
        {"id": "dashscope", "name": "通义千问/文心", "provider": "dashscope"},
        {"id": "deepseek", "name": "DeepSeek", "provider": "deepseek"},
    ]
    return {"data": models}


def _require_user(authorization: str = Header(...)):
    if not authorization.startswith("Bearer "):
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="未登录")
    token = authorization[7:]
    user_id = validate_session(token)
    if not user_id:
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="Token 无效或已过期")
    return user_id
