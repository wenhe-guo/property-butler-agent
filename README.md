# 物业智能管家 Agent

基于 LangChain + 通义千问构建的物业智能服务 Agent，支持 6 个业务工具的 Function Calling 自主调用，业务数据通过 SQLite 持久化。

用户用自然语言提问，模型自主判断需要调用哪个工具、提取参数、执行查询或写入，再把结果组织成人话返回。

## 功能特性

| 工具 | 功能 | 示例提问 |
|---|---|---|
| `query_property_fee` | 按房号查询物业费欠缴金额 | 「3-201 物业费交了吗」 |
| `query_parking_fee` | 查询车位号、月租、缴费状态与到期日 | 「我的车位停到什么时候」 |
| `register_repair` | 登记报修，生成工单号并落库 | 「空调不制冷，要报修」 |
| `query_repair_status` | 按工单号查询处理状态与维修师傅 | 「R44594 修好没」 |
| `register_complaint` | 登记投诉，生成投诉编号并落库 | 「楼上半夜装修，我要投诉」 |
| `query_announcements` | 按类型查询小区公告 | 「最近有什么通知」 |

**工具自主编排**：用户只问停车费时，模型会主动追加查询物业费欠缴并一并提醒。这不是代码硬编码的流程，而是模型基于工具描述自主决策。

## 技术栈

| 组件 | 说明 |
|---|---|
| FastAPI + Uvicorn | HTTP 服务与接口定义 |
| LangChain | 工具绑定与 Agent 链路编排 |
| 通义千问 qwen4-max | 大模型，Function Calling |
| SQLite | 业务数据持久化 |

## 项目结构
## 项目结构

```
property-butler-2.0/
├── main.py                 # 程序入口，只做装配：建 app、挂中间件、注册 router
├── config.py               # 密钥与端口配置（从 .env 读取，不进仓库）
├── routers/
│   └── chat.py             # 对话路由：POST /chat、POST /chat/reset、GET /chat/sessions
├── services/
│   ├── llm_service.py      # 模型调用 + 工具编排（依赖 langchain_openai）
│   ├── memory.py           # 会话记忆 ChatMemory + 会话池（只依赖 langchain_core）
│   ├── tools.py            # 6 个业务工具（@tool 装饰，含 SQLite 读写）
│   └── database.py         # SQLite 初始化与建表
├── tests/
│   └── test_memory.py      # 会话隔离 / 裁剪不拆工具对 / reset 三个单元测试
├── pytest.ini              # 让 pytest 从任意目录都能找到 services 包
└── requirements.txt
```

## 会话隔离（v3.0）

同一个 `session_id` 对应一份独立的对话记忆，不同业主之间不串上下文。
历史里保存的是**完整消息对象**（含带 `tool_calls` 的 `AIMessage`），不是纯文本，
所以多轮工具调用不会出现「无主工具返回」导致的 400。

| 接口 | 说明 |
|---|---|
| `POST /chat` | 一次对话，**必须带 `session_id`**（前端生成并保存，同一用户复用同一个） |
| `POST /chat/reset` | 清空指定会话的记忆 |
| `GET /chat/sessions` | 调试用，查看当前活跃会话 |

请求示例：

```json
{ "message": "1-101 物业费多少钱", "session_id": "u_1001" }
```

> 记忆当前存在进程内存里，重启即失效，多实例也无法共享。
> 生产环境应替换为 Redis 并加 TTL——隔离逻辑已就位，存储层是可替换的。

## 测试

```bash
pip install -r requirements.txt
pytest -v
```

三个用例覆盖 v3.0 的核心逻辑，**不调用真实模型**（纯逻辑测试，秒级完成）：

| 用例 | 防的是什么 |
|---|---|
| `test_session_isolation` | 两个会话的记忆被写成同一个对象（业主之间串上下文） |
| `test_trim_keeps_tool_pairs` | 裁剪历史时把 `AIMessage(tool_calls)` 和 `ToolMessage` 拆开，导致接口 400 |
| `test_reset_session` | reset 之后拿到的还是旧对象，记忆没真清掉 |

> 这三个用例都做过**变异验证**：故意把修好的逻辑改回错误写法，确认测试会变红。
> 红了才说明测试有效，否则可能是「假绿」。