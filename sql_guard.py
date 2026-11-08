"""
SQL 安全与执行（对应项目难点二「SQL 安全」）

三层防护，只允许「只读分析」，禁止任何写操作：
  1. SQLGlot AST 校验：解析 SQL，只放行 SELECT/UNION 等只读语句，
     拦截 DROP / DELETE / UPDATE / INSERT / CREATE / ALTER 等危险操作
  2. 只读数据库连接：以只读模式打开 SQLite + PRAGMA query_only=ON（双保险）
  3. 执行限制：查询超时（progress handler）+ 结果行数上限
"""

import sqlite3

import sqlglot
from sqlglot import exp

# 顶层只读语句白名单
READ_ONLY_STMTS = (exp.Select, exp.Union, exp.Except, exp.Intersect)
# 危险节点黑名单（即便藏在子查询/CTE 里也要拦）
FORBIDDEN = (exp.Insert, exp.Update, exp.Delete, exp.Drop, exp.Create, exp.Alter)

MAX_ROWS = 500            # 结果最多返回 500 行
QUERY_STEPS = 5_000_000   # SQLite 虚拟机执行步数上限（近似「查询超时」，足够正常分析查询）


def validate_sql(sql):
    """校验 SQL 是否只读且语法合法。返回 (ok, 错误信息)。"""
    if not sql or not sql.strip():
        return False, "SQL 为空"
    try:
        stmts = sqlglot.parse(sql, read="sqlite")
    except Exception as e:
        return False, f"SQL 语法错误：{e}"
    if not stmts:
        return False, "SQL 为空"

    for stmt in stmts:
        # 顶层必须是只读语句
        if not isinstance(stmt, READ_ONLY_STMTS):
            return False, f"禁止执行 {type(stmt).__name__}，仅允许只读 SELECT 查询"
        # 深度扫描，拦截任何危险节点
        for node in stmt.walk():
            if isinstance(node, FORBIDDEN):
                return False, f"检测到危险操作 {type(node).__name__}，已拦截"
    return True, "OK"


def execute_readonly(sql, db_path, max_rows=MAX_ROWS):
    """只读执行 SQL。返回 (columns, rows, truncated)。调用前必须先 validate_sql。"""
    uri = f"file:{db_path}?mode=ro"
    conn = sqlite3.connect(uri, uri=True, timeout=5)
    try:
        conn.execute("PRAGMA query_only = ON")
        cur = conn.cursor()

        def _timeout():
            raise sqlite3.OperationalError("查询超时（执行步数超过上限）")

        conn.set_progress_handler(_timeout, QUERY_STEPS)
        cur.execute(sql)
        cols = [d[0] for d in cur.description] if cur.description else []
        rows = cur.fetchmany(max_rows + 1)
        truncated = len(rows) > max_rows
        rows = rows[:max_rows]
        return cols, rows, truncated
    finally:
        conn.close()
