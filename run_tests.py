"""
测试脚本：验证 Data Agent 的核心非大模型部分（确定性测试，不消耗 API）

覆盖：SQL 安全校验 / 只读执行 / Schema RAG 检索 / Schema 一致性
运行：python run_tests.py
"""

import os
import sqlite3

import sql_guard
from schema import SCHEMA, RELATIONSHIPS, table_names

DB_PATH = os.path.join("data", "ecommerce.db")

TESTS = []


def test(name):
    def deco(fn):
        TESTS.append((name, fn))
        return fn
    return deco


@test("SQL 安全：合法聚合 SELECT 放行")
def t1():
    ok, _ = sql_guard.validate_sql("SELECT region, SUM(amount) FROM orders GROUP BY region")
    return ok


@test("SQL 安全：合法 JOIN 放行")
def t2():
    ok, _ = sql_guard.validate_sql(
        "SELECT o.order_id, c.name FROM orders o JOIN customers c ON o.customer_id=c.customer_id")
    return ok


@test("SQL 安全：拦截 DROP")
def t3():
    ok, _ = sql_guard.validate_sql("DROP TABLE orders")
    return not ok


@test("SQL 安全：拦截 DELETE")
def t4():
    ok, _ = sql_guard.validate_sql("DELETE FROM orders WHERE 1=1")
    return not ok


@test("SQL 安全：拦截 INSERT")
def t5():
    ok, _ = sql_guard.validate_sql("INSERT INTO orders VALUES (1)")
    return not ok


@test("SQL 安全：拦截 UPDATE")
def t6():
    ok, _ = sql_guard.validate_sql("UPDATE orders SET amount=0")
    return not ok


@test("SQL 安全：拦截多语句 SELECT;DROP")
def t7():
    ok, _ = sql_guard.validate_sql("SELECT 1; DROP TABLE x")
    return not ok


@test("SQL 安全：拦截语法错误")
def t8():
    ok, _ = sql_guard.validate_sql("SELEC bad syntax")
    return not ok


@test("只读执行：查询返回正确列与行")
def t9():
    cols, rows, _ = sql_guard.execute_readonly(
        "SELECT region, COUNT(*) n FROM orders GROUP BY region", DB_PATH)
    return cols == ["region", "n"] and len(rows) == 4


@test("只读执行：拦截写操作")
def t10():
    try:
        sql_guard.execute_readonly("DELETE FROM orders", DB_PATH)
        return False
    except sqlite3.OperationalError:
        return True
    except Exception:
        return False


@test("只读执行：结果行数上限截断")
def t11():
    cols, rows, trunc = sql_guard.execute_readonly("SELECT * FROM order_items", DB_PATH)
    return trunc is True and len(rows) == sql_guard.MAX_ROWS


@test("Schema RAG：销售问题检索到订单相关表")
def t12():
    import schema_rag
    names, _ = schema_rag.retrieve("各地区的销售额", top_k=5)
    return "orders" in names


@test("Schema RAG：库存问题检索到库存表")
def t13():
    import schema_rag
    names, _ = schema_rag.retrieve("各仓库的库存情况", top_k=5)
    return "inventory" in names


@test("Schema 一致性：所有表都在数据库中")
def t14():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    db_tables = {r[0] for r in cur.fetchall()}
    conn.close()
    return set(table_names()) == db_tables


@test("Schema 一致性：外键关系引用合法字段")
def t15():
    def has(t, c):
        for tbl in SCHEMA:
            if tbl["name"] == t:
                return any(col["name"] == c for col in tbl["columns"])
        return False

    for a, b in RELATIONSHIPS:
        ta, ca = a.split(".")
        tb, cb = b.split(".")
        if not (has(ta, ca) and has(tb, cb)):
            return False
    return True


def main():
    print("=" * 60)
    print("  Data Agent 测试报告")
    print("=" * 60)
    passed = 0
    for name, fn in TESTS:
        try:
            ok = bool(fn())
        except Exception as e:
            print(f"  [ERROR] {name}: {type(e).__name__}: {e}")
            continue
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}")
        passed += int(ok)
    print("-" * 60)
    print(f"  共 {len(TESTS)} 项，通过 {passed} 项，失败 {len(TESTS) - passed} 项")
    print("=" * 60)
    return 0 if passed == len(TESTS) else 1


if __name__ == "__main__":
    raise SystemExit(main())
