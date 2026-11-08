"""
Schema RAG：把数据库表结构「向量化」并做语义检索（Text-to-SQL 的关键一步）

为什么需要它？大模型不能凭空知道你的库有哪些表。表少时可以全塞进 Prompt，
但真实企业几百张表会爆 token 且干扰 SQL 生成。Schema RAG 的做法：
  1. 离线：把每张表的中文描述（表名 + 业务含义 + 字段列表）向量化存起来
  2. 在线：把用户问题也向量化，用余弦相似度检索最相关的 top-k 张表
  3. 只把相关表的详细结构塞进 Prompt（其余表只给一行简介）

这样既省 token，又提高了 SQL 准确率。这里复用 rag-demo 的 embedding 方案：
fastembed + bge-small-zh（ONNX 轻量，免 PyTorch，国内走 hf-mirror）。

运行：python schema_rag.py build   # 建索引（离线，一次）
"""

import os
import sys
import json

# 国内访问 HuggingFace 的兼容设置：走镜像 + 关闭 xet 加速
os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")
os.environ.setdefault("HF_HUB_DISABLE_XET", "1")

import numpy as np
from fastembed import TextEmbedding

from schema import SCHEMA, table_names

EMBED_MODEL = "BAAI/bge-small-zh-v1.5"
INDEX_DIR = "vector_index"
CHUNKS_PATH = os.path.join(INDEX_DIR, "schema_chunks.json")
VECTORS_PATH = os.path.join(INDEX_DIR, "schema_vectors.npy")


def table_chunk(table):
    """把一张表拼成一段用于 embedding 的文本（含字段与业务含义）。"""
    cols = "、".join(c["name"] for c in table["columns"])
    desc = "；".join(f"{c['name']}:{c['description']}" for c in table["columns"])
    return f"表 {table['name']}：{table['description']}。字段：{cols}。字段含义：{desc}"


def build_index():
    """离线建索引：每张表 -> 一个向量，存到 vector_index/。"""
    print("正在加载 embedding 模型...")
    model = TextEmbedding(model_name=EMBED_MODEL)
    chunks = [table_chunk(t) for t in SCHEMA]
    vectors = []
    for v in model.embed(chunks):
        arr = np.asarray(v, dtype=np.float32)
        vectors.append(arr / np.linalg.norm(arr))  # 归一化，点积 = 余弦相似度
    vectors = np.stack(vectors)
    os.makedirs(INDEX_DIR, exist_ok=True)
    np.save(VECTORS_PATH, vectors)
    with open(CHUNKS_PATH, "w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False, indent=1)
    print(f"Schema RAG 索引已建：{len(chunks)} 张表 -> {INDEX_DIR}/")


_model = None


def _embed(text):
    """把一段文本编码成归一化向量（复用已缓存的 embedding 模型）。"""
    global _model
    if _model is None:
        _model = TextEmbedding(model_name=EMBED_MODEL)
    arr = np.asarray(list(_model.embed([text]))[0], dtype=np.float32)
    return arr / np.linalg.norm(arr)


def retrieve(query, top_k=5):
    """检索最相关的 top_k 张表，返回 (表名列表, [(表名, 相似度), ...])。"""
    with open(CHUNKS_PATH, "r", encoding="utf-8") as f:
        chunks = json.load(f)
    vectors = np.load(VECTORS_PATH)
    q = _embed(query)
    scores = vectors @ q
    idx = np.argsort(scores)[::-1][:top_k]
    names = [table_names()[i] for i in idx]
    return names, [(table_names()[i], float(scores[i])) for i in idx]


def build_prompt_context(query, top_k=5):
    """根据问题检索相关表，拼出给 SQL 生成用的 schema 上下文。

    相关表给完整字段，无关表只给一行简介（模型若需要可再用 get_schema 工具查看）。
    """
    relevant, _ = retrieve(query, top_k)
    relevant_set = set(relevant)
    lines = ["数据库表结构（相关表已展开完整字段）："]
    for t in SCHEMA:
        if t["name"] in relevant_set:
            lines.append(f"\n表 {t['name']}：{t['description']}")
            for c in t["columns"]:
                lines.append(f"  - {c['name']} ({c['type']}): {c['description']}")
        else:
            lines.append(f"\n表 {t['name']}（其它，如需可调用 get_schema 查看）：{t['description']}")
    return "\n".join(lines)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "build":
        build_index()
    else:
        print("用法：python schema_rag.py build")
