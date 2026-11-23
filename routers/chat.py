""" 对话路由
- POST /chat           一次对话（必须带 session_id）
- POST /chat/reset     清空某个会话的记忆
- GET  /chat/sessions  调试用：看当前有几个活跃会话
"""
from fastapi import APIRouter
from pydantic import BaseModel
from services.llm_service import chat_with_llm, reset_session, list_sessions

router = APIRouter(prefix="/chat", tags=["对话"])


class ChatRequest(BaseModel):
    message: str
    session_id: str


class ResetRequest(BaseModel):
    session_id: str


@router.post("")
async def chat(request: ChatRequest):
    """一次对话。session_id 由前端生成并保存，同一个人多次对话要传同一个。"""
    try:
        reply = chat_with_llm(request.message, request.session_id)
        return {
            "reply": reply,
            "session_id": request.session_id,
            "agent_status": "运行中"
        }
    except Exception as e:
        return {
            "reply": f"出错了：{str(e)}",
            "session_id": request.session_id,
            "agent_status": "异常"
        }


@router.post("/reset")
async def reset(request: ResetRequest):
    """清空指定会话的记忆。"""
    reset_session(request.session_id)
    return {"ok": True, "session_id": request.session_id}


@router.get("/sessions")
async def sessions():
    """调试用：当前活跃会话列表。"""
    ids = list_sessions()
    return {"count": len(ids), "sessions": ids}