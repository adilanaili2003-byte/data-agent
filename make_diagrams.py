"""
生成三张交付物图（PNG，保存到 docs/）：
1. 系统架构图（docs/系统架构图.png）
2. 数据库 ER 图（docs/数据库ER图.png）
3. 核心业务流程图（docs/业务流程图.png）

运行：python make_diagrams.py
"""

import os
import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import matplotlib.patheffects as pe


# ============================================================
# 1. 全局样式配置
# ============================================================

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False

plt.rcParams["figure.facecolor"] = "#F8FAFC"
plt.rcParams["savefig.facecolor"] = "#F8FAFC"
plt.rcParams["font.size"] = 9
plt.rcParams["text.color"] = "#1E293B"


DOCS = "docs"

# 主色：深海蓝
BLUE = "#315C9B"
BLUE_L = "#EDF3FB"
BLUE_B = "#B8CBE3"

# 辅助色：青绿色
GREEN = "#168B75"
GREEN_L = "#EAF6F2"

# 强调色：暖琥珀色
ORANGE = "#C98235"
ORANGE_L = "#FBF2E7"

# 中性色
GRAY = "#64748B"
TEXT = "#1E293B"
WHITE = "#FFFFFF"

# 阴影效果
BOX_SHADOW = [
    pe.SimplePatchShadow(
        offset=(1.5, -1.5),
        shadow_rgbFace=(0.15, 0.23, 0.35),
        alpha=0.10
    ),
    pe.Normal()
]


# ============================================================
# 2. 基础绘图组件
# ============================================================

def box(
    ax,
    x,
    y,
    w,
    h,
    text,
    fc=BLUE_L,
    ec=BLUE,
    fs=10,
    bold=False,
    tc=TEXT
):
    """绘制带圆角、边框和轻量阴影的矩形框。"""

    patch = FancyBboxPatch(
        (x, y),
        w,
        h,
        boxstyle="round,pad=0.025,rounding_size=0.10",
        fc=fc,
        ec=ec,
        linewidth=1.5,
        zorder=2,
        antialiased=True
    )

    patch.set_path_effects(BOX_SHADOW)
    ax.add_patch(patch)

    ax.text(
        x + w / 2,
        y + h / 2,
        text,
        ha="center",
        va="center",
        fontsize=fs,
        zorder=3,
        fontweight="bold" if bold else "normal",
        color=tc,
        linespacing=1.3
    )


def arrow(
    ax,
    x1,
    y1,
    x2,
    y2,
    color=BLUE,
    style="-|>",
    lw=1.6,
    ls="-"
):
    """绘制柔和的连接箭头。"""

    patch = FancyArrowPatch(
        (x1, y1),
        (x2, y2),
        arrowstyle=style,
        mutation_scale=13,
        color=color,
        linewidth=lw,
        linestyle=ls,
        connectionstyle="arc3,rad=0",
        capstyle="round",
        joinstyle="round",
        zorder=1
    )

    ax.add_patch(patch)


def new_ax(w=12, h=8):
    """创建统一风格的画布。"""

    fig, ax = plt.subplots(figsize=(12, 8), dpi=140)

    # 画布范围保持原样
    ax.set_xlim(0, w)
    ax.set_ylim(0, h)

    ax.axis("off")

    fig.patch.set_facecolor("#F8FAFC")
    ax.set_facecolor("#F8FAFC")

    return fig, ax


def save(fig, name):
    """保存图片。"""

    path = os.path.join(DOCS, name)

    fig.savefig(
        path,
        bbox_inches="tight",
        facecolor="#F8FAFC",
        edgecolor="none",
        dpi=180
    )

    plt.close(fig)

    print("已生成：", path)


# ============================================================
# 3. 系统架构图
# ============================================================

def draw_architecture():

    fig, ax = new_ax()

    # 标题
    ax.text(
        6,
        7.7,
        "Data Agent 系统架构",
        ha="center",
        fontsize=19,
        fontweight="bold",
        color="#172F50"
    )

    # 用户层
    box(
        ax,
        4.4, 6.9, 3.2, 0.6,
        "用户（浏览器 / 命令行）",
        fc=WHITE,
        ec=GRAY,
        fs=10.5,
        bold=True
    )

    # 接入层
    box(
        ax,
        4.4, 5.8, 3.2, 0.7,
        "接入层\nFastAPI（webapp.py）/ CLI（main.py）",
        fc=BLUE_L,
        ec=BLUE,
        fs=9.5
    )

    # Agent 编排层
    box(
        ax,
        4.4, 4.5, 3.2, 0.9,
        "LangGraph 编排层\nagent 节点 <-> tools 节点（条件边循环）",
        fc="#E5EDF9",
        ec=BLUE,
        fs=9.5,
        bold=True
    )

    # 工具层
    box(
        ax,
        4.4, 3.0, 3.2, 1.1,
        "工具层（6 个 Tool Calling）\nlist_tables · get_schema · run_sql\nanalyze_data · make_chart · write_report",
        fc=GREEN_L,
        ec=GREEN,
        fs=9
    )

    # 数据与安全层
    box(
        ax,
        4.4, 1.2, 3.2, 1.4,
        "数据与安全层\nSQLGlot 只读校验 + SQLite 只读连接\nSchema RAG 向量索引（vector_index）\n行数 / 超时限制",
        fc=ORANGE_L,
        ec=ORANGE,
        fs=9
    )

    # 外部模型
    box(
        ax,
        9.0, 5.2, 2.4, 0.7,
        "DeepSeek API\n（deepseek-chat）",
        fc=WHITE,
        ec=GRAY,
        fs=9
    )

    # 向量化模型
    box(
        ax,
        9.0, 3.9, 2.4, 0.7,
        "fastembed\nbge-small-zh（向量化）",
        fc=WHITE,
        ec=GRAY,
        fs=9
    )

    # 主流程箭头
    arrow(ax, 6, 6.9, 6, 6.5)
    arrow(ax, 6, 5.8, 6, 5.4)
    arrow(ax, 6, 4.5, 6, 4.1)
    arrow(ax, 6, 3.0, 6, 2.6)

    # 外部服务连接
    arrow(
        ax,
        7.6, 4.9,
        9.0, 5.2,
        color=GRAY,
        style="<|-|>",
        lw=1.4
    )

    arrow(
        ax,
        7.6, 4.1,
        9.0, 3.9,
        color=GRAY,
        style="<|-|>",
        lw=1.4
    )

    # Schema RAG 说明
    ax.text(
        9.0,
        3.4,
        "Schema RAG 检索\n用 fastembed 向量化",
        ha="center",
        fontsize=8,
        color=GRAY,
        linespacing=1.3
    )

    save(fig, "系统架构图.png")


# ============================================================
# 4. 数据库 ER 图
# ============================================================

def draw_er():

    from schema import SCHEMA

    fig, ax = new_ax(w=12, h=10)

    # 标题
    ax.text(
        6,
        9.65,
        "数据库 ER 图（电商模拟数据，8 张表）",
        ha="center",
        fontsize=18,
        fontweight="bold",
        color="#172F50"
    )

    # 三列布局（x, y 为左下角）
    # 所有原始坐标保持不变
    pos = {
        "regions":     (0.3, 7.2),
        "customers":   (0.3, 3.9),
        "suppliers":   (0.3, 1.0),
        "orders":      (4.3, 5.9),
        "returns":     (4.3, 2.3),
        "order_items": (8.3, 6.3),
        "products":    (8.3, 3.0),
        "inventory":   (8.3, 0.3),
    }

    W, HEAD = 3.4, 0.55
    ROW = 0.42

    centers = {}

    for name, (x, y) in pos.items():

        t = next(t for t in SCHEMA if t["name"] == name)

        n = len(t["columns"])
        h = HEAD + ROW * n

        # 表名标题栏
        header = FancyBboxPatch(
            (x, y + h - HEAD),
            W,
            HEAD,
            boxstyle="round,pad=0.015,rounding_size=0.08",
            fc=BLUE,
            ec=BLUE,
            linewidth=1.3,
            zorder=2
        )

        header.set_path_effects(BOX_SHADOW)
        ax.add_patch(header)

        ax.text(
            x + W / 2,
            y + h - HEAD / 2,
            name,
            ha="center",
            va="center",
            fontsize=11,
            fontweight="bold",
            color=WHITE,
            zorder=3
        )

        # 表字段区域
        body = FancyBboxPatch(
            (x, y),
            W,
            h - HEAD,
            boxstyle="round,pad=0.015,rounding_size=0.06",
            fc=WHITE,
            ec=BLUE_B,
            linewidth=1.2,
            zorder=2
        )

        body.set_path_effects(BOX_SHADOW)
        ax.add_patch(body)

        # 字段信息
        for i, c in enumerate(t["columns"]):

            mark = (
                "PK"
                if "PRIMARY" in c["type"]
                else ("FK" if "外键" in c["description"] else "")
            )

            line = c["name"] + (f" ({mark})" if mark else "")

            ax.text(
                x + 0.12,
                y + h - HEAD - ROW * (i + 1) + ROW / 2,
                line,
                ha="left",
                va="center",
                fontsize=6.8,
                color=TEXT,
                zorder=3
            )

        centers[name] = (x + W / 2, y + h / 2)

    # 关系连线（边到边，1 : N）
    # 所有箭头坐标保持不变

    def er_line(p1, p2, lp):

        arrow(
            ax,
            p1[0],
            p1[1],
            p2[0],
            p2[1],
            color=GRAY,
            style="<|-|>",
            lw=1.2
        )

        ax.text(
            lp[0],
            lp[1],
            "1 : N",
            ha="center",
            va="center",
            fontsize=7.5,
            color=GRAY,
            zorder=4
        )

    er_line(
        (3.7, 5.435),
        (4.3, 7.645),
        (3.95, 6.6)
    )

    er_line(
        (3.7, 8.315),
        (4.3, 7.645),
        (3.95, 8.05)
    )

    er_line(
        (7.7, 7.645),
        (8.3, 7.835),
        (8.0, 7.85)
    )

    er_line(
        (10.0, 6.07),
        (10.0, 6.3),
        (10.25, 6.18)
    )

    er_line(
        (6.0, 5.9),
        (6.0, 5.37),
        (6.25, 5.63)
    )

    er_line(
        (8.3, 4.535),
        (7.7, 3.835),
        (8.1, 4.1)
    )

    er_line(
        (10.0, 3.0),
        (10.0, 2.95),
        (10.25, 2.97)
    )

    # 主键与外键说明
    ax.text(
        0.3,
        9.4,
        "PK = 主键　FK = 外键",
        fontsize=8.5,
        color=GRAY
    )

    save(fig, "数据库ER图.png")


# ============================================================
# 5. 核心业务流程图
# ============================================================

def draw_flow():

    fig, ax = new_ax(w=12, h=9)

    # 标题
    ax.text(
        6,
        8.65,
        "核心业务流程（自然语言 → 分析报告）",
        ha="center",
        fontsize=18,
        fontweight="bold",
        color="#172F50"
    )

    cx = 6
    H = 0.62

    # 所有步骤及坐标保持不变
    steps = [
        (8.0, "① 用户输入自然语言问题"),
        (7.1, "② 理解意图 + Schema RAG 检索相关表"),
        (6.2, "③ 大模型生成 SQL"),
        (5.3, "④ SQLGlot 只读校验"),
        (4.4, "⑤ 只读执行 SQL（SQLite · 行数/超时限制）"),
        (3.5, "⑥ Pandas 数据分析"),
        (2.6, "⑦ Plotly 生成图表"),
        (1.7, "⑧ 生成 Markdown 报告"),
        (0.8, "⑨ 输出结论 + 图表 + 报告"),
    ]

    # 绘制流程节点
    for y, txt in steps:

        if txt.startswith("⑨"):

            fc, ec = WHITE, GRAY

        else:

            fc, ec = (
                (BLUE_L, BLUE)
                if txt.startswith(("①", "②", "③", "④"))
                else (GREEN_L, GREEN)
            )

        box(
            ax,
            cx - 2.6,
            y,
            5.2,
            H,
            txt,
            fc=fc,
            ec=ec,
            fs=10.3
        )

    # 主流程箭头
    for i in range(len(steps) - 1):

        arrow(
            ax,
            cx,
            steps[i][0],
            cx,
            steps[i + 1][0] + H
        )

    # ④ 校验不合法 → 回环到 ③（左侧）

    y44 = 5.3 + H / 2
    y33 = 6.2 + H / 2

    arrow(
        ax,
        cx - 2.6,
        y44,
        1.2,
        y44,
        color=ORANGE,
        lw=1.3
    )

    arrow(
        ax,
        1.2,
        y44,
        1.2,
        y33,
        color=ORANGE,
        lw=1.3
    )

    arrow(
        ax,
        1.2,
        y33,
        cx - 2.6,
        y33,
        color=ORANGE,
        lw=1.3
    )

    ax.text(
        1.2,
        (y44 + y33) / 2,
        "不合法\n拦截/重写",
        fontsize=7.5,
        color=ORANGE,
        ha="center",
        va="center",
        linespacing=1.3
    )

    ax.text(
        cx + 0.25,
        5.15,
        "合法",
        fontsize=8,
        color=GREEN
    )

    # ⑤ 复杂 SQL → 人工确认（HITL），右侧分支

    box(
        ax,
        8.95,
        4.4,
        2.55,
        0.85,
        "复杂 SQL？\n人工确认（HITL）",
        fc=ORANGE_L,
        ec=ORANGE,
        fs=8.3
    )

    arrow(
        ax,
        cx + 2.6,
        4.4 + H / 2,
        8.95,
        4.4 + H / 2,
        color=ORANGE,
        style="<|-|>",
        lw=1.3
    )

    save(fig, "业务流程图.png")


# ============================================================
# 6. 主程序
# ============================================================

if __name__ == "__main__":

    os.makedirs(DOCS, exist_ok=True)

    draw_architecture()

    draw_er()

    draw_flow()

    print("\n三张图全部生成完毕。")