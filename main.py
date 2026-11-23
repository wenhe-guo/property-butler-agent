""" 物业智能管家3.0 - 程序入口
只做装配：创建 app、挂中间件、注册路由、启动服务
业务逻辑全部下沉到 routers/ 和 services/
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from config import PORT
from routers import chat

# 创建FastAPI应用实例
app = FastAPI(
    title="物业智能管家3.0",
    description="基于Agent的物业管理数字员工系统（会话隔离版）",
    version="3.0.0"
)

# 配置跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册业务路由：对话相关全部交给 routers/chat.py
app.include_router(chat.router)


@app.get("/")
async def root():
    return {
        "status": "running",
        "service": "物业智能管家3.0",
        "version": "3.0.0"
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    print("=" * 50)
    print("  物业智能管家3.0 启动中...")
    print(f"  访问地址：http://localhost:{PORT}")
    print(f"  API文档：http://localhost:{PORT}/docs")
    print("=" * 50)
    uvicorn.run("main:app", host="0.0.0.0", port=PORT, reload=True)