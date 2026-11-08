"""
Agent 主循环（用 LangGraph 建模）

LangGraph 把「大模型决策 → 调用工具 → 观察结果 → 再决策」这个循环，
显式地建模成一个「图」：

    START → agent 节点 →（条件边）→ tools 节点 → agent 节点 → ... → END
             ▲ 若模型返回 tool_calls 就去 tools，否则结束

节点：
  agent ：调用 DeepSeek（带工具定义），让它决定「下一步调用哪个工具」或「给出最终答案」
  tools ：执行模型要调用的工具，把结果作为 tool 消息追加回去

「Schema RAG」发生在 agent 节点第一次运行时：把用户问题向量化，
检索最相关的表结构，拼进系统提示，帮模型写出更准的 SQL。
"""

import os
import sys
import json
from typing import TypedDict

# 防止 Windows GBK 控制台打印 emoji/特殊字符时崩溃：无法编码的字符用 ? 替代，而非抛异常
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(errors="replace")
    sys.stderr.reconfigure(errors="replace")

from openai import OpenAI
from dotenv import load_dotenv
from langgraph.graph import StateGraph, START, END

import schema_rag
from tools import TOOL_DEFS, execute_tool, Runtime
from schema import RELATIONSHIPS, METRIC_DEFS

load_dotenv()

MODEL = os.environ.get("DATA_AGENT_MODEL", "deepseek-chat")
TODAY = "2026-11-08"

SYSTEM_PROMPT_TMPL = """你是数据分析助手，能通过工具查询数据库、计算、画图、写报告。
按「理解问题 → 查库 → 分析 → 可视化 → 报告」的思路逐步完成用户需求。

【数据库背景】
- 数据库时间范围：2025-11-01 ~ 2026-10-31；今天是 {today}。
- 「最近三个月」= 2026-08 ~ 2026-10。

【业务口径】
{metrics}

【表关系】
{relations}

【当前相关表结构（已按问题检索）】
{schema}

【规则】
1. 写 SQL 前，先用 get_schema 确认要用的表字段名（若上面结构里字段已够，可直接 run_sql）。
2. 只写 SELECT 查询；禁止任何写操作（DROP/DELETE/UPDATE/INSERT）。
3. 一次 run_sql 查一步；查完再用 analyze_data / make_chart 做后续分析。
4. 需要多步时按顺序来，不要一步塞太复杂。
5. 最终用中文向用户解释结论，并可调用 write_report 输出报告。
"""


class State(TypedDict):
    messages: list


def _llm():
    return OpenAI(api_key=os.environ["DEEPSEEK_API_KEY"], base_url="https://api.deepseek.com")


client = _llm()


def _agent_node(state):
    messages = state["messages"]

    # 第一次运行时注入 Schema RAG 上下文（系统提示只加一次）
    if not any(m["role"] == "system" for m in messages):
        user_q = next(m["content"] for m in messages if m["role"] == "user")
        schema_ctx = schema_rag.build_prompt_context(user_q)
        system = SYSTEM_PROMPT_TMPL.format(
            today=TODAY,
            metrics="\n".join("- " + m for m in METRIC_DEFS),
            relations="\n".join("- " + a + " -> " + b for a, b in RELATIONSHIPS),
            schema=schema_ctx,
        )
        messages = [{"role": "system", "content": system}] + messages

    resp = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        tools=TOOL_DEFS,
        temperature=0.2,
    )
    msg = resp.choices[0].message
    assistant = {"role": "assistant", "content": msg.content or ""}
    if msg.tool_calls:
        assistant["tool_calls"] = [
            {"id": tc.id, "type": "function",
             "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
            for tc in msg.tool_calls
        ]
    return {"messages": messages + [assistant]}


def _tool_node(state, runtime):
    messages = state["messages"]
    new_msgs = []
    for tc in messages[-1].get("tool_calls", []):
        name = tc["function"]["name"]
        try:
            args = json.loads(tc["function"]["arguments"] or "{}")
        except json.JSONDecodeError:
            args = {}
        print(f"\n[工具] 调用工具：{name}  {tc['function']['arguments']}")
        result = execute_tool(runtime, name, args)
        print(f"   -> {result[:300]}")
        runtime.trace.append({"tool": name, "args": args, "result": result})
        new_msgs.append({"role": "tool", "tool_call_id": tc["id"],
                         "name": name, "content": result})
    return {"messages": messages + new_msgs}


def _route(state):
    """条件边：模型返回了工具调用就走 tools，否则结束。"""
    last = state["messages"][-1]
    if last.get("tool_calls"):
        return "tools"
    return END


def build_agent(runtime):
    g = StateGraph(State)
    g.add_node("agent", _agent_node)
    g.add_node("tools", lambda s: _tool_node(s, runtime))
    g.add_edge(START, "agent")
    g.add_conditional_edges("agent", _route, {"tools": "tools", END: END})
    g.add_edge("tools", "agent")
    return g.compile()


def run_agent(graph, user_query):
    """跑一次完整对话，返回最终回复文本。"""
    final = graph.invoke({"messages": [{"role": "user", "content": user_query}]},
                         config={"recursion_limit": 40})
    last = final["messages"][-1]
    return last["content"] if last["role"] == "assistant" else ""
