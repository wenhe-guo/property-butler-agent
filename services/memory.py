""" 会话记忆模块 v3.1

设计要点：
1. 只依赖 langchain_core，绝不 import langchain_openai
   —— 单元测试加载本模块不会被模型 SDK 拖慢 20 秒
2. 记忆管理本来就跟"调模型"无关，拆开是关注点分离，不是为测试打的补丁
"""
from typing import Dict, List

from langchain_core.messages import HumanMessage, SystemMessage

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


# ============ 单个会话的记忆 ============

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


# ============ 会话池 ============

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