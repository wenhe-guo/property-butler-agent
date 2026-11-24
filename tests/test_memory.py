"""v3.0 核心逻辑测试

不调真实模型，只测我自己写的逻辑：
1. 会话隔离
2. 裁剪不拆散工具调用对
3. reset 真能清掉
"""
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage

from services.memory import (
    ChatMemory,
    get_memory,
    reset_session,
    list_sessions,
)


def test_session_isolation():
    """两个不同的 session_id 拿到的是两份完全独立的记忆"""
    mem_a = get_memory("TEST_AAA")
    mem_b = get_memory("TEST_BBB")

    assert mem_a is not mem_b

    mem_a.add_message(HumanMessage(content="我住 1-101"))

    assert len(mem_a.messages) == 1
    assert len(mem_b.messages) == 0

    reset_session("TEST_AAA")
    reset_session("TEST_BBB")


def test_trim_keeps_tool_pairs():
    """裁剪历史时，AIMessage(tool_calls) 和它的 ToolMessage 不能被拆开"""
    mem = ChatMemory(max_turns=2)

    for i in range(1, 5):
        mem.add_message(HumanMessage(content=f"查{i}-101的物业费"))
        mem.add_message(AIMessage(
            content="",
            tool_calls=[{
                "id": f"call_{i}",
                "name": "query_property_fee",
                "args": {"room": f"{i}-101"},
            }],
        ))
        mem.add_message(ToolMessage(content=f"{i}00元", tool_call_id=f"call_{i}"))
        mem.add_message(AIMessage(content=f"{i}-101物业费{i}00元"))

    assert len(mem.messages) == 8
    assert isinstance(mem.messages[0], HumanMessage)

    declared = set()
    for msg in mem.messages:
        if isinstance(msg, AIMessage) and msg.tool_calls:
            for tc in msg.tool_calls:
                declared.add(tc["id"])
        elif isinstance(msg, ToolMessage):
            assert msg.tool_call_id in declared, f"孤儿 ToolMessage: {msg.tool_call_id}"


def test_reset_session():
    """reset 之后，同一个 session_id 拿到的是全新的空记忆"""
    mem = get_memory("TEST_RESET")
    mem.add_message(HumanMessage(content="我住 3-301"))
    assert len(mem.messages) == 1

    reset_session("TEST_RESET")

    # 重新取，必须是全新的空对象，不是原来那个
    mem2 = get_memory("TEST_RESET")
    assert mem2 is not mem
    assert len(mem2.messages) == 0
    assert "TEST_RESET" in list_sessions()

    # reset 一个根本不存在的 session 不能崩
    reset_session("NOT_EXIST_XYZ")

    # 收尾，别把测试数据留在全局字典里
    reset_session("TEST_RESET")