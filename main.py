"""
物业智能管家2.0 - 程序入口
启动FastAPI服务，定义API接口
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
from config import PORT
from services.llm_service import chat_with_llm

# 创建FastAPI应用实例
app = FastAPI(
    title="物业智能管家2.0",
    description="基于Agent的物业管理数字员工系统",
    version="2.0.0"
)

# 配置跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {
        "status": "running",
        "service": "物业智能管家2.0",
        "version": "2.0.0"
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


class ChatRequest(BaseModel):
    message: str


@app.post("/chat")
async def chat(request: ChatRequest):
    try:
        reply = chat_with_llm(request.message)
        return {
            "reply": reply,
            "intent": "已接入LLM",
            "agent_status": "运行中"
        }
    except Exception as e:
        return {
            "reply": f"出错了：{str(e)}",
            "intent": "error",
            "agent_status": "异常"
        }


if __name__ == "__main__":
    print("=" * 50)
    print("  物业智能管家2.0 启动中...")
    print(f"  访问地址：http://localhost:{PORT}")
    print(f"  API文档：http://localhost:{PORT}/docs")
    print("=" * 50)
    uvicorn.run("main:app", host="0.0.0.0", port=PORT, reload=True)