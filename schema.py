"""
数据库 Schema 定义（表 + 字段 + 中文业务含义）

这是 Text-to-SQL 的「地图」：大模型要写出正确的 SQL，必须先知道
有哪些表、每个表有哪些字段、字段是什么业务含义。中文描述尤其关键——
字段名 customer_id 看不出业务，但「客户ID（主键，关联 orders.customer_id）」就清楚了。

同时这份 SCHEMA 也是 Schema RAG 的数据源（见 schema_rag.py）。
"""

SCHEMA = [
    {
        "name": "customers",
        "description": "客户信息表：每个客户的基本资料与所在地区",
        "columns": [
            {"name": "customer_id", "type": "INTEGER PRIMARY KEY", "description": "客户ID（主键）"},
            {"name": "name", "type": "TEXT", "description": "客户姓名"},
            {"name": "region", "type": "TEXT", "description": "客户所在地区（华东/华南/华北/西南）"},
            {"name": "city", "type": "TEXT", "description": "客户所在城市"},
            {"name": "signup_date", "type": "DATE", "description": "注册日期"},
            {"name": "vip_level", "type": "TEXT", "description": "会员等级（普通/银卡/金卡）"},
        ],
    },
    {
        "name": "orders",
        "description": "订单表：每笔订单的主信息（下单时间、状态、地区、金额）",
        "columns": [
            {"name": "order_id", "type": "INTEGER PRIMARY KEY", "description": "订单ID（主键）"},
            {"name": "customer_id", "type": "INTEGER", "description": "下单客户ID（外键，关联 customers.customer_id）"},
            {"name": "order_date", "type": "DATE", "description": "下单日期"},
            {"name": "status", "type": "TEXT", "description": "订单状态（已完成/已发货/待付款/已取消）"},
            {"name": "region", "type": "TEXT", "description": "订单所属地区（冗余自客户，便于按地区统计）"},
            {"name": "payment_method", "type": "TEXT", "description": "支付方式（微信/支付宝/银行卡）"},
            {"name": "amount", "type": "REAL", "description": "订单实付金额（元）"},
        ],
    },
    {
        "name": "order_items",
        "description": "订单明细表：每笔订单买了哪些商品、各买几件（一行一个商品）",
        "columns": [
            {"name": "item_id", "type": "INTEGER PRIMARY KEY", "description": "明细ID（主键）"},
            {"name": "order_id", "type": "INTEGER", "description": "所属订单ID（外键，关联 orders.order_id）"},
            {"name": "product_id", "type": "INTEGER", "description": "商品ID（外键，关联 products.product_id）"},
            {"name": "quantity", "type": "INTEGER", "description": "购买数量"},
            {"name": "unit_price", "type": "REAL", "description": "成交单价（元）"},
            {"name": "discount", "type": "REAL", "description": "折扣率（0~1，0表示无折扣）"},
        ],
    },
    {
        "name": "products",
        "description": "商品表：商品的分类、品牌、价格与成本",
        "columns": [
            {"name": "product_id", "type": "INTEGER PRIMARY KEY", "description": "商品ID（主键）"},
            {"name": "name", "type": "TEXT", "description": "商品名称"},
            {"name": "category", "type": "TEXT", "description": "商品品类（手机/家电/服饰/食品/美妆）"},
            {"name": "brand", "type": "TEXT", "description": "品牌"},
            {"name": "cost", "type": "REAL", "description": "成本价（元）"},
            {"name": "price", "type": "REAL", "description": "零售价（元）"},
        ],
    },
    {
        "name": "regions",
        "description": "地区维度表：各地区的基本信息与负责人",
        "columns": [
            {"name": "region", "type": "TEXT PRIMARY KEY", "description": "地区名（主键，华东/华南/华北/西南）"},
            {"name": "region_name", "type": "TEXT", "description": "地区全称"},
            {"name": "manager", "type": "TEXT", "description": "区域负责人姓名"},
            {"name": "province_count", "type": "INTEGER", "description": "覆盖省份数量"},
        ],
    },
    {
        "name": "suppliers",
        "description": "供应商表：为各商品供货的供应商信息",
        "columns": [
            {"name": "supplier_id", "type": "INTEGER PRIMARY KEY", "description": "供应商ID（主键）"},
            {"name": "name", "type": "TEXT", "description": "供应商名称"},
            {"name": "category", "type": "TEXT", "description": "供货品类"},
            {"name": "city", "type": "TEXT", "description": "供应商所在城市"},
            {"name": "rating", "type": "REAL", "description": "供应商评分（1~5）"},
        ],
    },
    {
        "name": "inventory",
        "description": "库存表：各商品在不同仓库的库存数量",
        "columns": [
            {"name": "inventory_id", "type": "INTEGER PRIMARY KEY", "description": "库存记录ID（主键）"},
            {"name": "product_id", "type": "INTEGER", "description": "商品ID（外键，关联 products.product_id）"},
            {"name": "warehouse", "type": "TEXT", "description": "仓库名（华东仓/华南仓/华北仓/西南仓）"},
            {"name": "quantity", "type": "INTEGER", "description": "当前库存数量"},
            {"name": "updated_date", "type": "DATE", "description": "最后更新时间"},
        ],
    },
    {
        "name": "returns",
        "description": "退货表：退货记录及原因",
        "columns": [
            {"name": "return_id", "type": "INTEGER PRIMARY KEY", "description": "退货ID（主键）"},
            {"name": "order_id", "type": "INTEGER", "description": "原订单ID（外键，关联 orders.order_id）"},
            {"name": "product_id", "type": "INTEGER", "description": "退货商品ID（外键，关联 products.product_id）"},
            {"name": "return_date", "type": "DATE", "description": "退货日期"},
            {"name": "reason", "type": "TEXT", "description": "退货原因"},
            {"name": "refund_amount", "type": "REAL", "description": "退款金额（元）"},
        ],
    },
]

# 表之间的外键关系（用于 SQL 生成提示，也对应「表关系检索」这一难点）
RELATIONSHIPS = [
    ("orders.customer_id", "customers.customer_id"),
    ("orders.region", "regions.region"),
    ("order_items.order_id", "orders.order_id"),
    ("order_items.product_id", "products.product_id"),
    ("returns.order_id", "orders.order_id"),
    ("returns.product_id", "products.product_id"),
    ("inventory.product_id", "products.product_id"),
]

# 销售额业务口径（写进提示，避免模型算错公式）
METRIC_DEFS = [
    "销售额 = SUM(order_items.quantity * order_items.unit_price * (1 - order_items.discount))",
    "订单数 = COUNT(DISTINCT orders.order_id)",
    "客单价 = 销售额 / 订单数",
    "毛利率 = SUM((unit_price - cost) * quantity) / 销售额",
]


def get_table(name):
    for t in SCHEMA:
        if t["name"] == name:
            return t
    return None


def table_names():
    return [t["name"] for t in SCHEMA]
