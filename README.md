# 炒股大师 (Stock Master)

松散结构的A股量化交易脚本集合

## 📁 项目结构

```
stock-master/
├── scripts/              # 独立脚本目录
│   ├── db.py                # 数据库连接工具
│   ├── init_db.py           # 数据库初始化
│   ├── fetch_kline.py       # 获取日K线
│   ├── fetch_suspend.py     # 获取停复牌
│   ├── fetch_finance.py     # 获取财务指标
│   ├── select_technical.py  # 技术面选股
│   ├── select_fundamental.py # 基本面选股
│   ├── score_stocks.py      # 综合评分
│   └── execute_trade.py     # 交易执行
├── config/
│   └── .env                 # 配置文件
├── data/                    # 数据缓存目录
├── logs/                    # 日志目录
└── README.md
```

## 🚀 脚本使用说明

### 1. 环境配置

```bash
# 复制配置模板
cp config/.env.example config/.env

# 编辑配置
vim config/.env
```

`.env` 内容:
```
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=stock_master
```

### 2. 初始化数据库

```bash
cd scripts
python init_db.py
```

### 3. 数据获取脚本

**获取日K线数据**
```bash
# 单只股票
python fetch_kline.py --code 000001

# 多只股票
python fetch_kline.py --code 000001,000002,600000

# 获取最近60天
python fetch_kline.py --code 000001 --days 60

# 获取所有股票（耗时）
python fetch_kline.py --all --limit 100
```

**获取停复牌信息**
```bash
python fetch_suspend.py
python fetch_suspend.py --date 20240401
```

**获取财务指标**
```bash
python fetch_finance.py --code 000001
python fetch_finance.py --all --limit 50
```

### 4. 选股脚本

**技术面选股**
```bash
# 基础选股
python select_technical.py

# 只看均线多头排列
python select_technical.py --ma-bullish

# 提高最低分数
python select_technical.py --min-score 75

# 指定日期
python select_technical.py --date 2024-04-01
```

**基本面选股**
```bash
# 基础筛选
python select_fundamental.py

# 自定义条件
python select_fundamental.py --min-roe 15 --max-pe 30

# 只看高分
python select_fundamental.py --min-score 70
```

### 5. 评分脚本

```bash
# 查看评分
python score_stocks.py

# 更新数据库
python score_stocks.py --update-db

# 指定日期
python score_stocks.py --date 2024-04-01
```

### 6. 交易脚本

```bash
# 查看交易计划（默认）
python execute_trade.py --plan

# 模拟交易
python execute_trade.py --dry-run

# 实盘交易（危险！）
python execute_trade.py --live
```

## 🔄 典型工作流程

```bash
cd scripts

# 1. 初始化（只需一次）
python init_db.py

# 2. 每日更新数据
python fetch_kline.py --all --limit 500
python fetch_suspend.py

# 3. 选股
python select_technical.py --min-score 65

# 4. 评分
python score_stocks.py --update-db

# 5. 生成交易计划
python execute_trade.py --plan

# 6. 模拟执行
python execute_trade.py --dry-run
```

## 📊 数据库表结构

| 表名 | 用途 |
|------|------|
| `kline_daily` | 日K线数据（含技术指标） |
| `suspend_info` | 停复牌信息 |
| `stock_basic` | 股票基础信息 |
| `finance_indicator` | 财务指标 |
| `selection_result` | 选股结果 |
| `positions` | 持仓 |
| `trade_history` | 交易记录 |
| `account` | 资金账户 |

## ⚠️ 免责声明

本项目仅供学习和研究使用，不构成任何投资建议。股市有风险，投资需谨慎。
