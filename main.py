"""
命令行入口：用自然语言问数据

运行前（按顺序，各跑一次）：
  1. 配置 .env（DEEPSEEK_API_KEY）
  2. python seed_db.py           # 建库造数
  3. python schema_rag.py build  # 建 Schema RAG 索引
  4. python main.py              # 开始对话
"""

import os

from dotenv import load_dotenv
load_dotenv()

from agent import build_agent, run_agent
from tools import Runtime


def main():
    if not os.path.exists(".env"):
        print("[错误] 缺少 .env。请复制 .env.example 为 .env，填入 DEEPSEEK_API_KEY")
        return
    if not os.path.exists(os.path.join("data", "ecommerce.db")):
        print("[错误] 还没有数据库。请先运行：python seed_db.py")
        return
    if not os.path.exists(os.path.join("vector_index", "schema_vectors.npy")):
        print("[错误] 还没有 Schema RAG 索引。请先运行：python schema_rag.py build")
        return

    runtime = Runtime()
    graph = build_agent(runtime)

    print("=" * 60)
    print("  Data Agent —— 自然语言数据分析智能体")
    print("  输入自然语言问题，Agent 自动查库 → 分析 → 画图 → 出报告")
    print("  示例：帮我分析最近三个月各地区的销售额，找出下降最明显的地区")
    print("  输入 q 退出")
    print("=" * 60)

    while True:
        q = input("\n你：").strip()
        if q.lower() == "q":
            break
        if not q:
            continue
        try:
            answer = run_agent(graph, q)
            print("\nAI：" + (answer or "(无文本输出)"))
        except Exception as e:
            import traceback
            print(f"\n[错误] 运行出错：{type(e).__name__}: {e}")
            traceback.print_exc()


if __name__ == "__main__":
    main()
