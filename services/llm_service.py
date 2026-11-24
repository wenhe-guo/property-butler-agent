""" LLM服务模块 v3.1
封装通义千问API调用 + Agent串联 + 工具执行

v3.1 相对 v3.0 的三处改动：
1. 记忆管理整体下沉到 services/memory.py —— 本模块只管"调模型"，不再管"记什么"
   好处：测试导入 memory.py 时不会连带加载 langchain_openai（省掉约 20 秒）
2. 工具执行改 tool_map.get() —— 模型幻觉出不存在的工具名不会再 KeyError 500
3. ToolMessage 的 content 加了 str() —— 工具返回非字符串也不会报错
"""
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, ToolMessage

from config import QWEN_API_KEY
from services.tools import (
    query_property_fee,
    register_repair,
    query_repair_status,
    register_complaint,
    query_parking_fee,
    query_announcements,
)
# 记忆相关全部从 memory 模块导入（这里同时也做了 re-export，
# routers/chat.py 里 from services.llm_service import reset_session 依然可用，不用改）
from services.memory import (
    ChatMemory,
    get_memory,
    reset_session,
    list_sessions,
)

# ============ 模型初始化 ============

llm = ChatOpenAI(
    model="qwen4-max",
    api_key=QWEN_API_KEY,
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    temperature=0.7,
    max_tokens=1024,
)

tools = [
    query_property_fee,
    register_repair,
    query_repair_status,
    register_complaint,
    query_parking_fee,
    query_announcements,
]

llm_with_tools = llm.bind_tools(tools)

tool_map = {
    "query_property_fee": query_property_fee,
    "register_repair": register_repair,
    "query_repair_status": query_repair_status,
    "register_complaint": register_complaint,
    "query_parking_fee": query_parking_fee,
    "query_announcements": query_announcements,
}

# 一次对话里最多允许几轮工具调用，防止死循环
MAX_TOOL_ROUNDS = 5


# ============ 主流程 ============

def chat_with_llm(user_message: str, session_id: str = "default") -> str:
    """带会话隔离记忆的 Agent 对话

    session_id 不同 → 记忆完全隔离，A 业主问的房号 B 业主看不到。
    """
    mem = get_memory(session_id)

    # 先把用户这句话存进本会话的记忆
    mem.add_message(HumanMessage(content=user_message))

    for _ in range(MAX_TOOL_ROUNDS):
        # 带着完整历史（含 System Prompt）问模型
        response = llm_with_tools.invoke(mem.get_all())

        # 关键：存 response 对象本身，不是 response.content
        # 这样 tool_calls 字段才保得住
        mem.add_message(response)

        # 没调工具，就是最终回复
        if not response.tool_calls:
            return response.content

        # 调了工具：逐个执行，结果作为 ToolMessage 追加
        for tool_call in response.tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]

            # 用 get 而不是直接索引：模型偶尔会编出不存在的工具名，
            # 直接索引会 KeyError 把整个请求打成 500
            tool_func = tool_map.get(tool_name)
            if tool_func is None:
                result = f"工具 {tool_name} 不存在，请换个说法帮业主处理"
            else:
                try:
                    result = tool_func.invoke(tool_args)
                except Exception as e:
                    result = f"工具 {tool_name} 执行出错：{e}"

            # content 必须是字符串，工具返回 dict/list 时 str() 兜住
            mem.add_message(
                ToolMessage(content=str(result), tool_call_id=tool_call["id"])
            )

    return "抱歉，这个问题有点绕，我帮您转人工处理。"