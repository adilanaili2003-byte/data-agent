"""
步骤①：建库 + 造数（离线，跑一次即可）

生成一个模拟电商数据库 ecommerce.db，8 张表，覆盖 Text-to-SQL 需要的
「多表关联」场景（订单、客户、商品、地区、供应商、库存、退货）。

数据时间范围：2025-11-01 ~ 2026-10-31（12 个月）
约定「今天」= 2026-11-08，于是「最近三个月」= 2026-08 ~ 2026-10，方便演示。

为了让「找出销售额下降最明显的地区」有清晰答案，造数时让西南地区
在 2026-08 起逐月下滑，其它地区基本平稳（这是示例演示数据）。

运行：python seed_db.py
"""

import os
import random
import sqlite3
from datetime import date, timedelta

import numpy as np

from schema import SCHEMA

DB_PATH = os.path.join("data", "ecommerce.db")

random.seed(42)
np.random.seed(42)

REGIONS = ["华东", "华南", "华北", "西南"]
CITIES = {
    "华东": ["上海", "杭州", "南京", "苏州"],
    "华南": ["广州", "深圳", "厦门", "佛山"],
    "华北": ["北京", "天津", "青岛", "郑州"],
    "西南": ["成都", "重庆", "昆明", "贵阳"],
}
CATEGORIES = ["手机", "家电", "服饰", "食品", "美妆"]
BRANDS = {
    "手机": ["华为", "小米", "OPPO", "vivo"],
    "家电": ["美的", "格力", "海尔", "苏泊尔"],
    "服饰": ["优衣库", "李宁", "安踏", "波司登"],
    "食品": ["三只松鼠", "良品铺子", "百草味", "农夫山泉"],
    "美妆": ["完美日记", "花西子", "珀莱雅", "自然堂"],
}
PAY_METHODS = ["微信", "支付宝", "银行卡"]
STATUSES = ["已完成", "已发货", "待付款", "已取消"]
VIP_LEVELS = ["普通", "银卡", "金卡"]
REASONS = ["质量问题", "尺码/型号不合适", "与描述不符", "7天无理由", "物流损坏"]

TODAY = date(2026, 11, 8)
START = date(2025, 11, 1)
END = date(2026, 10, 31)
AVG_ORDER_VALUE = 500.0  # 平均客单价，用于估算每天订单数


def daterange(start, end):
    for n in range((end - start).days + 1):
        yield start + timedelta(days=n)


def weighted_choice(pairs):
    """pairs = [(value, weight), ...]，按权重随机选一个。"""
    vals, weights = zip(*pairs)
    return random.choices(vals, weights=weights, k=1)[0]


def month_factor(region, d):
    """各地区月度销售额因子：西南 2026-08 起逐月下滑，其它轻微波动。"""
    if region == "西南" and d >= date(2026, 8, 1):
        drop = (d.year - 2026) * 12 + (d.month - 8)  # 8/9/10 月 -> 0/1/2
        return 1 - 0.25 * (drop + 1)                 # 0.75 / 0.50 / 0.25
    return 1.0 + 0.15 * np.sin(d.year * 12 + d.month)


def build_db():
    os.makedirs("data", exist_ok=True)
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # ---- 建表（DDL 从 schema.py 自动拼）----
    for t in SCHEMA:
        cols = ", ".join(f"{c['name']} {c['type']}" for c in t["columns"])
        cur.execute(f"CREATE TABLE {t['name']} ({cols})")

    # ---- regions 地区维度表 ----
    for region in REGIONS:
        cur.execute(
            "INSERT INTO regions (region, region_name, manager, province_count) VALUES (?,?,?,?)",
            (region, region + "大区", random.choice(["张伟", "李娜", "王强", "刘敏"]),
             random.randint(3, 8)),
        )

    # ---- products 商品表（5 品类 × 10 个 = 50 个商品）----
    products = []
    for cat in CATEGORIES:
        for i in range(10):
            brand = random.choice(BRANDS[cat])
            cost = round(random.uniform(20, 300), 2)
            price = round(cost * random.uniform(1.5, 3.0), 2)
            name = f"{brand} {cat}{i + 1}号"
            products.append((cat, brand, cost, price, name))
    for pid, (cat, brand, cost, price, name) in enumerate(products, start=1):
        cur.execute(
            "INSERT INTO products (product_id, name, category, brand, cost, price) VALUES (?,?,?,?,?,?)",
            (pid, name, cat, brand, cost, price),
        )
    n_products = len(products)

    # ---- customers 客户表（800 人）----
    customers = []
    for cid in range(1, 801):
        region = random.choice(REGIONS)
        city = random.choice(CITIES[region])
        signup = START + timedelta(days=random.randint(0, 200))
        vip = weighted_choice([("普通", 0.7), ("银卡", 0.2), ("金卡", 0.1)])
        name = random.choice(["赵", "钱", "孙", "李", "周", "吴", "郑", "王"]) + \
               random.choice(["伟", "芳", "娜", "敏", "静", "磊", "军", "洋"])
        customers.append((cid, name, region, city, signup, vip))
    cur.executemany(
        "INSERT INTO customers (customer_id, name, region, city, signup_date, vip_level) VALUES (?,?,?,?,?,?)",
        customers,
    )
    region_customers = {r: [] for r in REGIONS}
    for cid, _, region, _, _, _ in customers:
        region_customers[region].append(cid)

    # ---- orders + order_items（订单 + 明细）----
    region_month_base = {r: random.uniform(80000, 120000) for r in REGIONS}
    order_id = 1
    for d in daterange(START, END):
        for region in REGIONS:
            base = region_month_base[region] * month_factor(region, d)
            mean_orders = base / 30.0 / AVG_ORDER_VALUE
            n_orders = int(max(0, np.random.normal(mean_orders, mean_orders * 0.5)))
            for _ in range(n_orders):
                cid = random.choice(region_customers[region])
                status = weighted_choice([("已完成", 0.6), ("已发货", 0.2),
                                          ("待付款", 0.1), ("已取消", 0.1)])
                pay = random.choice(PAY_METHODS)
                n_items = random.randint(1, 4)
                amount = 0.0
                items = []
                for _ in range(n_items):
                    pid = random.randint(1, n_products)
                    _, _, cost, price, _ = products[pid - 1]
                    qty = random.randint(1, 3)
                    unit = round(price * random.uniform(0.9, 1.0), 2)
                    disc = random.choice([0.0, 0.0, 0.0, 0.1, 0.2])
                    amount += qty * unit * (1 - disc)
                    items.append((pid, qty, unit, disc))
                amount = round(amount, 2)
                cur.execute(
                    "INSERT INTO orders (order_id, customer_id, order_date, status, region, payment_method, amount) "
                    "VALUES (?,?,?,?,?,?,?)",
                    (order_id, cid, d.isoformat(), status, region, pay, amount),
                )
                for pid, qty, unit, disc in items:
                    cur.execute(
                        "INSERT INTO order_items (order_id, product_id, quantity, unit_price, discount) "
                        "VALUES (?,?,?,?,?)",
                        (order_id, pid, qty, unit, disc),
                    )
                order_id += 1

    # ---- suppliers 供应商表（15 家）----
    all_cities = [c for cities in CITIES.values() for c in cities]
    for sid in range(1, 16):
        cat = random.choice(CATEGORIES)
        cur.execute(
            "INSERT INTO suppliers (supplier_id, name, category, city, rating) VALUES (?,?,?,?,?)",
            (sid, f"供应商{sid}", cat, random.choice(all_cities),
             round(random.uniform(3.0, 5.0), 1)),
        )

    # ---- inventory 库存表（每商品 × 4 仓库）----
    for pid in range(1, n_products + 1):
        for wh in [r + "仓" for r in REGIONS]:
            cur.execute(
                "INSERT INTO inventory (product_id, warehouse, quantity, updated_date) VALUES (?,?,?,?)",
                (pid, wh, random.randint(0, 2000), END.isoformat()),
            )

    # ---- returns 退货表（已完成订单中约 3% 发生退货）----
    cur.execute("SELECT order_id, order_date, amount FROM orders WHERE status='已完成'")
    done_orders = cur.fetchall()
    for oid, odate, amount in random.sample(done_orders, k=int(len(done_orders) * 0.03)):
        pid = random.randint(1, n_products)
        rdate = (date.fromisoformat(odate) + timedelta(days=random.randint(1, 20))).isoformat()
        cur.execute(
            "INSERT INTO returns (order_id, product_id, return_date, reason, refund_amount) VALUES (?,?,?,?,?)",
            (oid, pid, rdate, random.choice(REASONS), round(amount * random.uniform(0.3, 1.0), 2)),
        )

    conn.commit()
    print("数据库已生成：", DB_PATH)
    for t in SCHEMA:
        cur.execute(f"SELECT COUNT(*) FROM {t['name']}")
        print(f"  {t['name']}: {cur.fetchone()[0]} 行")
    conn.close()


if __name__ == "__main__":
    build_db()
