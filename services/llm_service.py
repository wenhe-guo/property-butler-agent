"""
LLM服务模块
封装通义千问API调用 + Agent串联 + 对话记忆
"""
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, ToolMessage
from config import QWEN_API_KEY

# System Prompt
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

# 初始化模型
llm = ChatOpenAI(
    model="qwen4-max",
    api_key=QWEN_API_KEY,
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    temperature=0.7,
    max_tokens=1024
)

# 绑定工具
from services.tools import (
    query_property_fee, register_repair,
    query_repair_status, register_complaint,
    query_parking_fee, query_announcements
)

tools = [query_property_fee, register_repair, query_repair_status, register_complaint, query_parking_fee, query_announcements]
llm_with_tools = llm.bind_tools(tools)

tool_map = {
    "query_property_fee": query_property_fee,
    "register_repair": register_repair,
    "query_repair_status": query_repair_status,
    "register_complaint": register_complaint,
    "query_parking_fee": query_parking_fee,
    "query_announcements": query_announcements,
}

class ChatMemory:
    """简单的对话记忆 - 记住最近10轮对话"""
    
    def __init__(self, max_turns=10):
        self.max_turns = max_turns
        self.messages = []  # 保存历史消息
    
    def add(self, role, content):
        """添加一条消息到记忆"""
        if role == "human":
            self.messages.append(HumanMessage(content=content))
        elif role == "ai":
            self.messages.append(AIMessage(content=content))
        elif role == "tool":
            self.messages.append(ToolMessage(content=content, tool_call_id=""))
        
        # 超出限制就删除最早的
        if len(self.messages) > self.max_turns * 2:
            self.messages = self.messages[-self.max_turns * 2:]
    
    def get_all(self):
        """获取完整对话历史"""
        return [SystemMessage(content=SYSTEM_PROMPT)] + self.messages
    
    def clear(self):
        """清空记忆"""
        self.messages = []


# 全局记忆实例
memory = ChatMemory()


def chat_with_llm(user_message: str) -> str:
    """
    带记忆的Agent对话
    """
    # 把历史消息 + 当前消息一起发给模型
    messages = memory.get_all()
    messages.append(HumanMessage(content=user_message))
    
    # 第一轮：模型判断要不要调工具
    response = llm_with_tools.invoke(messages)
    
    # 如果需要工具
    if response.tool_calls:
        memory.add("human", user_message)
        memory.add("ai", response.content)
        
        for tool_call in response.tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]
            tool_func = tool_map[tool_name]
            result = tool_func.invoke(tool_args)
            memory.messages.append(ToolMessage(
                content=result,
                tool_call_id=tool_call["id"]
            ))
        
        # 第二轮：模型根据工具结果生成回复
        messages = memory.get_all()
        final_response = llm_with_tools.invoke(messages)
        memory.add("ai", final_response.content)
        return final_response.content
    
    # 不需要工具
    memory.add("human", user_message)
    memory.add("ai", response.content)
    return response.content
# cd "D:\python agent\property-butler-2.0"