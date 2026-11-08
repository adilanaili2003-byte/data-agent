# Data Agent —— 自然语言数据分析智能体

>  **Agent / Tool Calling / Text-to-SQL / RAG / LangGraph / FastAPI / Docker**。
>
> 基于大语言模型与 Agent 工作流编排技术，实现自然语言到 SQL 查询、Python 数据分析及可视化报告生成的智能数据分析系统。

核心目标：

用户不需要掌握 SQL 或 Python，只需要通过自然语言描述分析需求，系统自动完成 **理解问题 → 查库(SQL) → Pandas 分析 → Plotly 画图 → 生成报告**。

例如：

用户输入：
分析最近三个月各地区的销售额变化，找出销售额下降最明显的地区，分析可能原因，并生成一份可视化分析报告。

系统自动完成：
1. 理解分析需求。
2. 检索数据库 Schema。
3. 确定需要查询的表和字段。
4. 生成 SQL 查询语句。
5. 验证 SQL 合法性与安全性。
6. 执行 SQL 并获取数据。
7. 使用 Pandas 进行数据分析。
8. 使用 Plotly 生成可视化图表。
9. 结合分析结果生成报告。
最终输出一份包含数据、图表、分析结论和建议的报告。
---

## 一、能做什么（演示效果）

```
你：帮我分析最近三个月各地区的销售额，找出下降最明显的地区，并生成分析报告。

Agent 自动：
  ① 理解问题     ② Schema RAG 检索相关表     ③ 生成 SQL
  ④ SQLGlot 安全校验  ⑤ 只读执行 SQL         ⑥ Pandas 算环比/降幅
  ⑦ Plotly 画柱状图   ⑧ 写 Markdown 报告      ⑨ 中文汇报结论
```

---

## 二、系统架构

```
用户自然语言问题
      │
      ▼
┌─────────────────────────────────────────────────┐
│           LangGraph 工作流（Agent 循环）           │
│                                                  │
│    ┌────────┐   有 tool_calls    ┌───────────┐   │
│    │ agent  ├──────────────────► │  tools     │   │
│    │(DeepSeek│                   │ 执行工具    │   │
│    │ 决策)   │◄──────────────────┤           │   │
│    └───┬────┘                    └───────────┘   │
│        │ 无 tool_calls（已能回答）                  │
│        ▼                                          │
│    最终答案 ──► 图表(HTML) / 报告(Markdown)         │
└─────────────────────────────────────────────────┘
    ▲  Schema RAG：问题向量化 → 检索最相关表结构
    ▲  SQL 安全：SQLGlot AST 校验 + 只读连接 + 行数/超时限制
    ▲  Human-in-the-Loop：复杂 SQL 执行前人工确认
```

**6 个工具（Tool Calling）**

| 工具 | 作用 |
|---|---|
| list_tables | 列出所有表及一句话说明 |
| get_schema | 查某张表的字段定义（写 SQL 前确认字段名） |
| run_sql | 只读 SQL 查询（自动安全校验 + 执行） |
| analyze_data | 用 Pandas 对查询结果做统计（环比/降幅/TopN） |
| make_chart | 用 Plotly 生成图表（HTML） |
| write_report | 写 Markdown 分析报告 |

---

## 三、技术栈

| 层 | 技术 |
|---|---|
| Agent 编排 | LangGraph（StateGraph + 条件边） |
| 大模型 | DeepSeek（OpenAI 兼容，`deepseek-chat`） |
| 向量检索 | fastembed + bge-small-zh（免 PyTorch，国内走 hf-mirror） |
| SQL 安全 | SQLGlot（AST 校验）+ SQLite 只读连接 |
| 数据 | SQLite（本地演示），架构已预留 PostgreSQL 切换 |
| 分析/可视化 | Pandas + Plotly |

---

## 四、快速开始

```bash
cd data-agent

# 1. 装依赖
pip install -r requirements.txt

# 2. 配置 API Key
#    复制 .env.example 为 .env，填入 DEEPSEEK_API_KEY

# 3. 建库造数（生成 8 张表的模拟电商数据，跑一次）
python seed_db.py

# 4. 建 Schema RAG 索引（首次会下载 embedding 模型约 100MB，之后离线）
python schema_rag.py build

# 5. 开始对话（命令行版）
python main.py

# 6. 网页版（演示 / 截图 / 录视频效果更好）
python webapp.py
# 浏览器会自动打开 http://127.0.0.1:8008
# 也可以双击「启动网页版.bat」
```

**推荐测试问题：**
- 帮我分析最近三个月各地区的销售额，找出下降最明显的地区
- 哪个品类的销售额最高？各品类占比多少？
- 最近一个月退单率最高的是哪个品类？

> 复杂 SQL（含 JOIN/GROUP BY）执行前会弹出 `确认执行？[y/n]`，这就是 Human-in-the-Loop。
> 想跳过确认，把 `.env` 里 `REQUIRE_SQL_CONFIRM` 改成 `0`。

---

## 五、项目结构

```
data-agent/
├── schema.py          # 数据库 Schema 定义（表/字段/中文业务含义）
├── seed_db.py         # 建库 + 造数（跑一次）
├── schema_rag.py      # Schema RAG：建索引 + 语义检索相关表
├── sql_guard.py       # SQL 安全：SQLGlot 校验 + 只读执行 + 行数/超时限制
├── tools.py           # 6 个工具的定义 + 实现（Tool Calling）
├── agent.py           # LangGraph 工作流：agent/tools 节点 + 条件边
├── main.py            # 命令行入口
├── data/ecommerce.db  # 生成的数据库（seed_db.py 产出）
├── charts/            # 生成的图表（make_chart 产出）
├── reports/           # 生成的报告（write_report 产出）
└── vector_index/      # Schema RAG 向量索引（schema_rag.py 产出）
```

---

## 六、四个技术难点是怎么解决的

**难点一：Text-to-SQL 准确率**
大模型不能凭空知道库结构。我做了「Schema RAG」：把每张表的中文描述向量化，用户问题也向量化，
检索最相关的 top-k 张表，只把相关表的详细结构塞进 Prompt。再叠加：字段中文描述、表关系、
业务口径（销售额=数量×单价×(1-折扣)）写进提示；SQL 执行报错后把错误回传让模型自动修复。

**难点二：SQL 安全（三层防护）**
1. SQLGlot AST 校验：只放行 SELECT/UNION，拦截 DROP/DELETE/UPDATE/INSERT/CREATE/ALTER；
2. SQLite 只读连接 + `PRAGMA query_only=ON`；
3. 查询超时（progress handler）+ 结果行数上限（500 行）。

**难点三：多步骤任务规划**
用 LangGraph 的 `agent → tools → agent` 循环 + 条件边（有 tool_calls 就继续调工具，否则结束），
实现「查库 → 分析 → 画图 → 报告」的多步动态路由，而不是写死一条流水线。

**难点四：人工介入（Human-in-the-Loop）**
复杂 SQL 执行前弹出确认，用户拒绝后模型会调整查询。演示用 `input()` 实现；
生产/网页版可升级为 LangGraph 的 `interrupt()` + 断点恢复。

## 七、交付物清单

| 交付物 | 位置 |
|---|---|
| 系统架构图 | `docs/系统架构图.png` |
| 数据库 ER 图 | `docs/数据库ER图.png` |
| 核心业务流程图 | `docs/业务流程图.png` |
| 测试报告（15/15 通过） | `docs/测试报告.md` |
| 运行示例  | `docs/运行示例.md` |

> 三张图可随时重新生成：`python make_diagrams.py`；测试可复跑：`python run_tests.py`。
