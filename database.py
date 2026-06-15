import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'repair_shop.db')

MAINTENANCE_INTERVAL = 5000


def get_connection():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS vehicles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        plate_number TEXT NOT NULL UNIQUE,
        brand_model TEXT NOT NULL,
        vin_code TEXT NOT NULL UNIQUE,
        last_maintenance_mileage INTEGER DEFAULT 0,
        created_at TEXT NOT NULL
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS parts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        code TEXT NOT NULL UNIQUE,
        price REAL NOT NULL,
        stock INTEGER NOT NULL DEFAULT 0,
        min_stock INTEGER NOT NULL DEFAULT 5,
        created_at TEXT NOT NULL
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS parts_transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        part_id INTEGER NOT NULL,
        quantity INTEGER NOT NULL,
        type TEXT NOT NULL,
        order_id INTEGER,
        note TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY (part_id) REFERENCES parts(id)
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS fault_codes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT NOT NULL UNIQUE,
        description TEXT NOT NULL,
        solution TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS work_orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        vehicle_id INTEGER NOT NULL,
        mileage INTEGER NOT NULL,
        fault_description TEXT NOT NULL,
        fault_code_id INTEGER,
        labor_cost REAL NOT NULL DEFAULT 0,
        total_cost REAL NOT NULL DEFAULT 0,
        status TEXT NOT NULL DEFAULT 'NORMAL',
        created_at TEXT NOT NULL,
        updated_at TEXT,
        FOREIGN KEY (vehicle_id) REFERENCES vehicles(id),
        FOREIGN KEY (fault_code_id) REFERENCES fault_codes(id)
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS work_order_parts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        work_order_id INTEGER NOT NULL,
        part_id INTEGER NOT NULL,
        part_name TEXT NOT NULL,
        part_code TEXT NOT NULL,
        unit_price REAL NOT NULL,
        quantity INTEGER NOT NULL,
        subtotal REAL NOT NULL,
        FOREIGN KEY (work_order_id) REFERENCES work_orders(id),
        FOREIGN KEY (part_id) REFERENCES parts(id)
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS purchase_suggestions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        part_id INTEGER NOT NULL,
        part_name TEXT NOT NULL,
        current_stock INTEGER NOT NULL,
        suggested_quantity INTEGER NOT NULL,
        created_at TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'PENDING',
        FOREIGN KEY (part_id) REFERENCES parts(id)
    )
    ''')

    conn.commit()
    conn.close()


def migrate_db():
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("PRAGMA table_info(work_orders)")
        cols = [row[1] for row in cursor.fetchall()]
        if 'status' not in cols:
            cursor.execute("ALTER TABLE work_orders ADD COLUMN status TEXT NOT NULL DEFAULT 'NORMAL'")
        if 'updated_at' not in cols:
            cursor.execute("ALTER TABLE work_orders ADD COLUMN updated_at TEXT")
        conn.commit()
    except Exception:
        conn.rollback()
    conn.close()


def seed_sample_data():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM parts")
    if cursor.fetchone()[0] == 0:
        sample_parts = [
            ('机油', 'P001', 88.00, 20, 5),
            ('机油滤清器', 'P002', 35.00, 15, 5),
            ('空气滤清器', 'P003', 45.00, 12, 5),
            ('刹车片', 'P004', 280.00, 8, 3),
            ('火花塞', 'P005', 65.00, 3, 5),
            ('轮胎', 'P006', 580.00, 2, 4),
            ('变速箱油', 'P007', 120.00, 10, 5),
            ('雨刮片', 'P008', 40.00, 6, 5),
        ]
        for p in sample_parts:
            cursor.execute(
                "INSERT INTO parts (name, code, price, stock, min_stock, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (p[0], p[1], p[2], p[3], p[4], datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            )

    cursor.execute("SELECT COUNT(*) FROM fault_codes")
    if cursor.fetchone()[0] == 0:
        sample_faults = [
            ('P0100', '空气流量传感器故障', '检查并更换空气流量传感器，清理进气管道'),
            ('P0171', '系统过稀（第1排）', '检查进气系统漏气，清洗喷油嘴，检查燃油压力'),
            ('P0300', '随机/多缸失火', '检查火花塞、点火线圈、燃油喷射系统'),
            ('P0301', '1缸失火', '更换1缸火花塞，检查点火线圈和喷油嘴'),
            ('P0420', '催化剂系统效率低于阈值', '检查三元催化器，排查氧传感器'),
            ('P0500', '车速传感器故障', '检查车速传感器及线路连接'),
            ('B1000', '控制模块故障', '使用诊断仪读取详细故障码，检查ECU供电'),
            ('C0035', '左前轮速度传感器电路', '检查ABS传感器及齿圈，清理传感器探头'),
        ]
        for f in sample_faults:
            cursor.execute(
                "INSERT INTO fault_codes (code, description, solution, created_at) VALUES (?, ?, ?, ?)",
                (f[0], f[1], f[2], datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            )

    conn.commit()
    conn.close()
