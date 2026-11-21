import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "property.db")


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    cursor = conn.cursor()

    # 物业费表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS property_fees (
            room_number TEXT PRIMARY KEY,
            amount REAL NOT NULL,
            parking_space TEXT,
            parking_monthly_fee REAL DEFAULT 300,
            parking_status TEXT DEFAULT '已缴',
            parking_expire TEXT
        )
    """)

    # 报修工单表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS repairs (
            order_id TEXT PRIMARY KEY,
            room_number TEXT NOT NULL,
            content TEXT NOT NULL,
            status TEXT DEFAULT '待处理',
            worker TEXT DEFAULT '',
            worker_phone TEXT DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)

    # 投诉/建议表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS complaints (
            ticket_id TEXT PRIMARY KEY,
            room_number TEXT NOT NULL,
            content TEXT NOT NULL,
            status TEXT DEFAULT '待处理',
            created_at TEXT NOT NULL
        )
    """)

    # 公告表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS announcements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            category TEXT NOT NULL,
            date TEXT NOT NULL,
            content TEXT NOT NULL
        )
    """)

    # 插入初始模拟数据（只在表为空时插入）
    cursor.execute("SELECT COUNT(*) FROM property_fees")
    if cursor.fetchone()[0] == 0:
        cursor.executemany(
            "INSERT INTO property_fees VALUES (?, ?, ?, ?, ?, ?)",
            [
                ("3-201", 1580.5, "B2-A056", 300, "已缴", "2026-12-31"),
                ("1-102", 0, "B1-B012", 300, "已缴", "2026-11-30"),
                ("5-601", 3200.0, "B2-C088", 300, "未缴", "2026-09-30"),
                ("2-305", 890.0, "B1-A033", 300, "已缴", "2027-01-31"),
            ]
        )

    cursor.execute("SELECT COUNT(*) FROM repairs")
    if cursor.fetchone()[0] == 0:
        cursor.executemany(
            "INSERT INTO repairs VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            [
                ("R10001", "3-201", "水管漏水", "已派单", "张师傅", "13800001111", "2026-10-08 10:00", "2026-10-09 09:00"),
                ("R10002", "1-102", "门锁损坏", "处理中", "李师傅", "13800002222", "2026-10-08 14:00", "2026-10-09 10:00"),
                ("R10003", "5-601", "电路跳闸", "已完成", "王师傅", "13800003333", "2026-10-07 09:00", "2026-10-08 16:30"),
            ]
        )

    cursor.execute("SELECT COUNT(*) FROM announcements")
    if cursor.fetchone()[0] == 0:
        cursor.executemany(
            "INSERT INTO announcements (title, category, date, content) VALUES (?, ?, ?, ?)",
            [
                ("10月15日小区消防演练通知", "通知", "2026-10-12", "定于10月15日上午9:00在小区广场进行消防演练，请业主配合。"),
                ("10月20日B2层水管维修停水通知", "停水", "2026-10-11", "10月20日8:00-18:00 B2层停水，请相关业主提前储水。"),
                ("重阳节业主联欢活动报名", "活动", "2026-10-10", "10月21日重阳节，小区将举办业主联欢活动，欢迎报名参与。"),
                ("10月25日小区供电设备检修停电通知", "停电", "2026-10-09", "10月25日9:00-12:00全小区停电检修，请提前做好准备。"),
            ]
        )

    conn.commit()
    conn.close()
    print(f"数据库初始化完成：{DB_PATH}")


# 初始化数据库
init_db()