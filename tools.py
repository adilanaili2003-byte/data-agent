"""
5 个工具：Schema 查询 / 只读 SQL / Pandas 分析 / Plotly 画图 / 写报告

这是「Agent + 多工具（Tool Calling）」的核心：大模型自己不会查库，
而是通过 function calling 调用下面这些工具，把「不会的活」交给代码做。

每个工具 = 一个 OpenAI function 定义（给模型看的说明）+ 一个实现函数（真正干活的）。
"""

import os
import sys
import io
import json
from datetime import datetime

import pandas as pd
import numpy as np

import sql_guard
from schema import get_table, table_names

DB_PATH = os.path.join("data", "ecommerce.db")


class Runtime:
    """工具间的共享状态：数据库路径、最近一次查询结果 df、确认开关等。"""

    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        self.df = None  # 最近一次 run_sql 的结果 DataFrame
        self.trace = []  # 工具调用轨迹（网页版可观测性展示用）
        self.require_confirm = os.environ.get("REQUIRE_SQL_CONFIRM", "1") == "1"


# ---------- 工具实现 ----------

def _fmt_table(df, max_rows=20):
    """把 DataFrame 手动格式化成 Markdown 表格（不依赖 tabulate）。"""
    d = df.head(max_rows)
    cols = list(d.columns)
    header = "| " + " | ".join(str(c) for c in cols) + " |"
    sep = "| " + " | ".join(["---"] * len(cols)) + " |"
    body = []
    for _, row in d.iterrows():
        body.append("| " + " | ".join("" if pd.isna(v) else str(v) for v in row) + " |")
    return "\n".join([header, sep] + body)


def tool_list_tables(runtime):
    lines = []
    for name in table_names():
        t = get_table(name)
        lines.append(f"- {name}：{t['description']}")
    return "数据库中的表：\n" + "\n".join(lines)


def tool_get_schema(runtime, tables):
    parts = []
    for name in tables:
        t = get_table(name)
        if t is None:
            parts.append(f"表 {name} 不存在。")
            continue
        cols = "\n".join(f"  - {c['name']} ({c['type']}): {c['description']}" for c in t["columns"])
        parts.append(f"表 {name}：{t['description']}\n{cols}")
    return "\n\n".join(parts)


def _is_complex(sql):
    up = sql.upper()
    return any(k in up for k in ["JOIN", "GROUP BY", "HAVING", "UNION", "(SELECT", "WITH "])


def tool_run_sql(runtime, sql):
    ok, err = sql_guard.validate_sql(sql)
    if not ok:
        return f"[SQL 被拦截] {err}"

    # 复杂查询执行前让用户确认 —— 这就是 Human-in-the-Loop
    if runtime.require_confirm and _is_complex(sql):
        print("\n" + "=" * 60)
        print("[警告] 检测到较复杂的 SQL，执行前请确认（只读操作，不会改数据）：")
        print("-" * 60)
        print(sql)
        print("-" * 60)
        ans = input("确认执行？[y/n]（直接回车 = 执行）：").strip().lower()
        if ans == "n":
            return "[用户拒绝执行该 SQL] 请改用更简单的方式，或向用户说明后调整查询。"

    try:
        cols, rows, truncated = sql_guard.execute_readonly(sql, runtime.db_path)
    except Exception as e:
        return f"[SQL 执行失败] {type(e).__name__}: {e}\n请根据报错修改 SQL 后重试。"

    runtime.df = pd.DataFrame(rows, columns=cols) if rows else pd.DataFrame(columns=cols)
    if runtime.df.empty:
        return "查询成功，但结果为空（0 行）。"
    out = f"查询成功，返回 {len(rows)} 行" + ("（已截断到前 500 行）" if truncated else "") + "：\n"
    out += _fmt_table(runtime.df)
    return out


def tool_analyze_data(runtime, code):
    if runtime.df is None:
        return "还没有查询结果。请先用 run_sql 查出数据，再调用 analyze_data。"

    df = runtime.df
    # 受限执行环境：只暴露 df/pd/np 和少量安全内置函数，去掉 __import__/open/eval 等。
    # （说明：这是「演示级」隔离，生产环境应放到 Docker/e2b 等真正沙箱里执行）
    safe_builtins = {
        "abs": abs, "min": min, "max": max, "sum": sum, "round": round,
        "len": len, "sorted": sorted, "range": range, "enumerate": enumerate,
        "zip": zip, "list": list, "dict": dict, "set": set, "tuple": tuple,
        "str": str, "int": int, "float": float, "bool": bool, "print": print,
    }
    g = {"__builtins__": safe_builtins, "df": df, "pd": pd, "np": np}

    buf = io.StringIO()
    old = sys.stdout
    sys.stdout = buf
    try:
        exec(code, g)
        result = g.get("result", None)
    except Exception as e:
        result = None
        buf.write(f"\n[代码执行报错] {type(e).__name__}: {e}")
    finally:
        sys.stdout = old

    printed = buf.getvalue().strip()
    parts = []
    if printed:
        parts.append(printed)
    if result is not None:
        parts.append(f"result = {result}")
    if not parts:
        parts.append("代码已执行（未打印任何输出，也未给 result 赋值）。")
    return "\n".join(parts)


def tool_make_chart(runtime, chart_type, x, y=None, color=None, title="图表"):
    if runtime.df is None:
        return "还没有查询结果。请先用 run_sql 查出数据，再调用 make_chart。"
    import plotly.express as px

    fn = {"bar": px.bar, "line": px.line, "pie": px.pie,
          "scatter": px.scatter, "area": px.area}.get(chart_type)
    if fn is None:
        return f"不支持的图表类型 {chart_type}，可选：bar/line/pie/scatter/area"
    try:
        if chart_type == "pie":
            fig = px.pie(runtime.df, names=x, values=y, title=title)
        else:
            fig = fn(runtime.df, x=x, y=y, color=color, title=title)
        os.makedirs("charts", exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.join("charts", f"{chart_type}_{ts}.html")
        fig.write_html(path)
        return f"图表已保存：{path}（可用浏览器打开查看）"
    except Exception as e:
        return (f"[画图失败] {type(e).__name__}: {e}。可能是指定的 x/y 字段不存在，"
                f"请根据最近查询结果的列名调整。")


def tool_write_report(runtime, title, content):
    os.makedirs("reports", exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join("reports", f"report_{ts}.md")
    full = f"# {title}\n\n> 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n{content}\n"
    with open(path, "w", encoding="utf-8") as f:
        f.write(full)
    return f"报告已保存：{path}\n\n报告内容：\n{full}"


# ---------- OpenAI 函数定义（给大模型看的说明） ----------

TOOL_DEFS = [
    {
        "type": "function",
        "function": {
            "name": "list_tables",
            "description": "列出数据库中的所有表及一句话说明。不确定有哪些表时先调用它。",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_schema",
            "description": "查看指定表的完整字段定义（含中文业务含义）。写 SQL 前用它确认字段名。",
            "parameters": {
                "type": "object",
                "properties": {
                    "tables": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "要查看的表名列表，如 [\"orders\", \"customers\"]",
                    }
                },
                "required": ["tables"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_sql",
            "description": "执行一条只读 SQL 查询（仅 SELECT，自动做安全校验）。返回结果表格。复杂查询执行前会请用户确认。",
            "parameters": {
                "type": "object",
                "properties": {
                    "sql": {"type": "string", "description": "要执行的 SQL（只能是 SELECT 查询）"}
                },
                "required": ["sql"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_data",
            "description": "用 pandas 对最近一次 run_sql 的结果做统计分析。参数是 Python 代码，变量 df 是最近查询结果的 DataFrame。可用变量：df、pd、np。把最终结论赋给 result 或直接 print。",
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {"type": "string", "description": "pandas 分析代码，操作变量 df"}
                },
                "required": ["code"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "make_chart",
            "description": "用 Plotly 基于最近一次 run_sql 的结果生成图表，保存为 HTML 文件。",
            "parameters": {
                "type": "object",
                "properties": {
                    "chart_type": {"type": "string", "enum": ["bar", "line", "pie", "scatter", "area"], "description": "图表类型"},
                    "x": {"type": "string", "description": "X 轴/分类字段名（列名）"},
                    "y": {"type": "string", "description": "Y 轴/数值字段名（列名），饼图可省略"},
                    "color": {"type": "string", "description": "分组颜色字段（可选）"},
                    "title": {"type": "string", "description": "图表标题"},
                },
                "required": ["chart_type", "x", "title"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_report",
            "description": "把最终分析结论写成 Markdown 报告并保存到 reports/ 目录。",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "报告标题"},
                    "content": {"type": "string", "description": "报告正文（Markdown 格式）"},
                },
                "required": ["title", "content"],
            },
        },
    },
]


def execute_tool(runtime, name, args):
    """根据工具名分发到具体实现。"""
    if name == "list_tables":
        return tool_list_tables(runtime)
    if name == "get_schema":
        return tool_get_schema(runtime, args.get("tables", []))
    if name == "run_sql":
        return tool_run_sql(runtime, args["sql"])
    if name == "analyze_data":
        return tool_analyze_data(runtime, args["code"])
    if name == "make_chart":
        return tool_make_chart(runtime, args["chart_type"], args.get("x"), args.get("y"),
                               args.get("color"), args.get("title", "图表"))
    if name == "write_report":
        return tool_write_report(runtime, args["title"], args["content"])
    return f"未知工具：{name}"
