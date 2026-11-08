"""
FastAPI 网页版入口

运行：python webapp.py
浏览器会自动打开 http://127.0.0.1:8000

网页版与命令行版的区别：网页版为演示效果，复杂 SQL 自动执行（不弹确认），
但会把每一步工具调用的轨迹返回给前端展示（可观测性）。Human-in-the-Loop 见 CLI 版。
"""

import os
import threading
import webbrowser

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

from agent import build_agent, run_agent
from tools import Runtime

app = FastAPI(title="Data Agent — 自然语言数据分析智能体")


class ChatReq(BaseModel):
    message: str


@app.get("/", response_class=HTMLResponse)
def index():
    with open(os.path.join("static", "index.html"), encoding="utf-8") as f:
        return f.read()


@app.post("/api/chat")
def chat(req: ChatReq):
    runtime = Runtime()
    runtime.require_confirm = False  # 网页版自动执行；HITL 见 CLI 版
    graph = build_agent(runtime)
    try:
        answer = run_agent(graph, req.message)
        return {"answer": answer, "trace": runtime.trace}
    except Exception as e:
        return JSONResponse(status_code=500, content={
            "error": f"{type(e).__name__}: {e}", "trace": runtime.trace})


def _check_ready():
    msgs = []
    if not os.path.exists(".env"):
        msgs.append("缺少 .env（DEEPSEEK_API_KEY）")
    if not os.path.exists(os.path.join("data", "ecommerce.db")):
        msgs.append("缺少数据库，请先运行 python seed_db.py")
    if not os.path.exists(os.path.join("vector_index", "schema_vectors.npy")):
        msgs.append("缺少 Schema RAG 索引，请先运行 python schema_rag.py build")
    return msgs


if __name__ == "__main__":
    import uvicorn

    PORT = 8008  # 本机 8000 已被其它服务（Enterprise Service Agent）占用，改用 8008
    for m in _check_ready():
        print(f"[警告] {m}")
    threading.Timer(1.5, lambda: webbrowser.open(f"http://127.0.0.1:{PORT}")).start()
    print(f"启动网页版：http://127.0.0.1:{PORT}")
    uvicorn.run(app, host="127.0.0.1", port=PORT, log_level="warning")
