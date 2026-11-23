""" LLM服务模块
封装通义千问API调用 + Agent串联 + 按会话隔离的对话记忆

v3.0 相对 2.0 的三处关键修复：
1. ChatMemory 不再全局单例，按 session_id 各存一份 —— 业主之间不串上下文
2. 记忆里存完整消息对象（含带 tool_calls 的 AIMessage）—— 修掉 400 隐患
3. 裁剪历史按 HumanMessage 边界整轮切 —— 不会把 AIMessage(tool_calls)+ToolMessage 拆开
"""
from typing import Dict, List

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, ToolMessage

from config import QWEN_API_KEY

# ============ System Prompt ============

SYSTEM_PROMPT = """你是"物业智能管家"，一个专业的物业管理AI助手。

## 你的职责
- 帮助业主查询物业费、报修进度等物业服务
- 回答小区相关的常见问题

## 你的语气
- 专业、热情、简洁

## 重要规则
- 当业主需要查询物业费或报修时，你必须使用工具，不要自己编造数据
- 不知道的事情就说"我帮您查询一下"
"""

# ============ 模型初始化 ============

llm = ChatOpenAI(
    model="qwen4-max",
    api_key=QWEN_API_KEY,
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    temperature=0.7,
    max_tokens=1024
)

# 绑定工具
from services.tools import (
    query_property_fee,
    register_repair,
    query_repair_status,
    register_complaint,
    query_parking_fee,
    query_announcements
)

tools = [
    query_property_fee,
    register_repair,
    query_repair_status,
    register_complaint,
    query_parking_fee,
    query_announcements
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


# ============ 会话记忆 ============

class ChatMemory:
    """单个会话的对话记忆

    跟 2.0 最大的区别：存的是完整消息对象，不是 content 字符串。
    带 tool_calls 的 AIMessage 原样保存，下一轮发回去才不会 400。
    """

    def __init__(self, max_turns: int = 10):
        self.max_turns = max_turns
        self.messages: List = []

    def add_message(self, message):
        """直接存完整消息对象（HumanMessage / AIMessage / ToolMessage）"""
        self.messages.append(message)
        self._trim()

    def _trim(self):
        """按 HumanMessage 边界整轮裁剪

        保证「AIMessage(带 tool_calls) + 它后面所有 ToolMessage」这一组
        永远在同一边，不会被切成两半。
        """
        if len(self.messages) <= self.max_turns * 2:
            return

        # 找出所有 HumanMessage 的位置，作为每一轮的起点
        turn_starts = [
            i for i, m in enumerate(self.messages)
            if isinstance(m, HumanMessage)
        ]

        if len(turn_starts) <= self.max_turns:
            return

        # 只保留最后 max_turns 轮
        cut = turn_starts[-self.max_turns]
        self.messages = self.messages[cut:]

    def get_all(self) -> List:
        """完整历史（含 System Prompt）"""
        return [SystemMessage(content=SYSTEM_PROMPT)] + self.messages

    def clear(self):
        self.messages = []


# 会话池：key 是 session_id，value 是该会话的记忆
_sessions: Dict[str, ChatMemory] = {}


def get_memory(session_id: str) -> ChatMemory:
    """拿到某个会话的记忆，没有就新建"""
    if session_id not in _sessions:
        _sessions[session_id] = ChatMemory()
    return _sessions[session_id]


def reset_session(session_id: str):
    """清空某个会话的记忆"""
    if session_id in _sessions:
        del _sessions[session_id]


def list_sessions() -> List[str]:
    """当前活跃会话列表（调试用）"""
    return list(_sessions.keys())


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
            tool_func = tool_map[tool_name]
            result = tool_func.invoke(tool_args)
            mem.add_message(
                ToolMessage(content=result, tool_call_id=tool_call["id"])
            )

    return "抱歉，这个问题有点绕，我帮您转人工处理。"


# cd "D:\python agent\property-butler-2.0"