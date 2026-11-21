"""
工具模块
物业管家可调用的工具函数，每个工具都带@tool装饰器和docstring描述
"""
from langchain.tools import tool
import random
from datetime import datetime
from services.database import get_conn


@tool
def query_property_fee(room_number: str) -> str:
    """根据房号查询物业费欠缴金额。参数：room_number - 房号，格式如 '3-201'"""
    conn = get_conn()
    row = conn.execute("SELECT amount FROM property_fees WHERE room_number = ?", (room_number,)).fetchone()
    conn.close()
    if row is None:
        return f"未查到房号{room_number}的物业费信息，请核对房号"
    amount = row["amount"]
    if amount == 0:
        return f"房号{room_number}物业费已缴清，无欠缴"
    return f"房号{room_number}欠缴物业费{amount}元"


@tool
def register_repair(room_number: str, content: str) -> str:
    """为业主登记报修。参数：room_number - 房号，content - 报修内容描述"""
    order_id = f"R{random.randint(10000, 99999)}"
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    conn = get_conn()
    conn.execute(
        "INSERT INTO repairs VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (order_id, room_number, content, "待处理", "", "", now, now)
    )
    conn.commit()
    conn.close()
    return f"报修已登记！工单号：{order_id}，房号：{room_number}，内容：{content}，预计24小时内上门处理"


@tool
def query_repair_status(order_id: str) -> str:
    """根据工单号查询报修处理进度。参数：order_id - 工单号，如 'R10001'"""
    conn = get_conn()
    row = conn.execute("SELECT * FROM repairs WHERE order_id = ?", (order_id,)).fetchone()
    conn.close()
    if row is None:
        return f"未查到工单号{order_id}的报修记录，请核对工单号"
    return f"工单{order_id}：状态={row['status']}，维修师傅={row['worker']}，电话={row['worker_phone']}，房号={row['room_number']}，内容={row['content']}"


@tool
def register_complaint(room_number: str, content: str) -> str:
    """为业主登记投诉或建议。参数：room_number - 房号，content - 投诉或建议内容"""
    ticket_id = f"C{random.randint(10000, 99999)}"
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    conn = get_conn()
    conn.execute(
        "INSERT INTO complaints VALUES (?, ?, ?, ?, ?)",
        (ticket_id, room_number, content, "待处理", now)
    )
    conn.commit()
    conn.close()
    return f"投诉/建议已受理！编号：{ticket_id}，房号：{room_number}，内容：{content}，物业将在3个工作日内回复您"


@tool
def query_parking_fee(room_number: str) -> str:
    """根据房号查询停车费缴纳情况。参数：room_number - 房号，格式如 '3-201'"""
    conn = get_conn()
    row = conn.execute(
        "SELECT parking_space, parking_monthly_fee, parking_status, parking_expire FROM property_fees WHERE room_number = ?",
        (room_number,)
    ).fetchone()
    conn.close()
    if row is None:
        return f"未查到房号{room_number}的停车位信息，请核对房号"
    if row["parking_status"] == "已缴":
        return f"房号{room_number}：车位{row['parking_space']}，月租{row['parking_monthly_fee']}元/月，已缴至{row['parking_expire']}"
    else:
        return f"房号{room_number}：车位{row['parking_space']}，月租{row['parking_monthly_fee']}元/月，️已过期({row['parking_expire']})，请及时续费"


@tool
def query_announcements(category: str) -> str:
    """查询小区最新公告。参数：category - 公告类别，可选值：'停水'、'停电'、'活动'、'通知'、'全部'"""
    conn = get_conn()
    if category == "全部":
        rows = conn.execute("SELECT * FROM announcements ORDER BY date DESC").fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM announcements WHERE category = ? ORDER BY date DESC", (category,)
        ).fetchall()
    conn.close()
    if not rows:
        return f"暂无'{category}'类别的公告"
    result = "\n".join([f"【{r['category']}】{r['title']}（{r['date']}）：{r['content']}" for r in rows])
    return f"相关公告：\n{result}"