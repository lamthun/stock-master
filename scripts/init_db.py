# -*- coding: utf-8 -*-
"""
数据库初始化脚本
创建所有必要的表

用法:
    python init_db.py
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, text
from db import get_engine

# 建表SQL
TABLES_SQL = [
    # K线数据表
    """
    CREATE TABLE IF NOT EXISTS kline_daily (
        id BIGINT AUTO_INCREMENT PRIMARY KEY,
        stock_code VARCHAR(10) NOT NULL COMMENT '股票代码',
        trade_date DATE NOT NULL COMMENT '交易日期',
        open_price DECIMAL(10, 4) NOT NULL COMMENT '开盘价',
        close_price DECIMAL(10, 4) NOT NULL COMMENT '收盘价',
        high_price DECIMAL(10, 4) NOT NULL COMMENT '最高价',
        low_price DECIMAL(10, 4) NOT NULL COMMENT '最低价',
        volume BIGINT NOT NULL COMMENT '成交量(手)',
        amount DECIMAL(20, 4) COMMENT '成交金额(元)',
        amplitude DECIMAL(6, 4) COMMENT '振幅(%)',
        pct_change DECIMAL(6, 4) COMMENT '涨跌幅(%)',
        change_amount DECIMAL(10, 4) COMMENT '涨跌额',
        turnover DECIMAL(6, 4) COMMENT '换手率(%)',
        ma5 DECIMAL(10, 4) COMMENT 'MA5',
        ma10 DECIMAL(10, 4) COMMENT 'MA10',
        ma20 DECIMAL(10, 4) COMMENT 'MA20',
        ma60 DECIMAL(10, 4) COMMENT 'MA60',
        bias DECIMAL(8, 4) COMMENT '乖离率',
        macd_dif DECIMAL(10, 4) COMMENT 'MACD DIF',
        macd_dea DECIMAL(10, 4) COMMENT 'MACD DEA',
        macd_hist DECIMAL(10, 4) COMMENT 'MACD HIST',
        rsi DECIMAL(6, 2) COMMENT 'RSI',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        UNIQUE KEY uk_stock_date (stock_code, trade_date),
        INDEX idx_stock_code (stock_code),
        INDEX idx_trade_date (trade_date),
        INDEX idx_code_date (stock_code, trade_date)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='日K线数据表';
    """,
    
    # 停复牌表
    """
    CREATE TABLE IF NOT EXISTS suspend_info (
        id BIGINT AUTO_INCREMENT PRIMARY KEY,
        stock_code VARCHAR(10) NOT NULL COMMENT '股票代码',
        stock_name VARCHAR(50) COMMENT '股票名称',
        suspend_date DATE COMMENT '停牌日期',
        resume_date DATE COMMENT '复牌日期',
        suspend_reason VARCHAR(255) COMMENT '停牌原因',
        is_suspended TINYINT(1) DEFAULT 1 COMMENT '是否停牌中 1=是 0=否',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        INDEX idx_stock_code (stock_code),
        INDEX idx_suspend_date (suspend_date),
        INDEX idx_is_suspended (is_suspended)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='停复牌信息表';
    """,
    
    # 股票基础信息表
    """
    CREATE TABLE IF NOT EXISTS stock_basic (
        id BIGINT AUTO_INCREMENT PRIMARY KEY,
        stock_code VARCHAR(10) NOT NULL COMMENT '股票代码',
        stock_name VARCHAR(50) COMMENT '股票名称',
        industry VARCHAR(50) COMMENT '所属行业',
        market VARCHAR(10) COMMENT '市场 sh/sz/bj',
        total_cap DECIMAL(20, 4) COMMENT '总市值',
        float_cap DECIMAL(20, 4) COMMENT '流通市值',
        list_date DATE COMMENT '上市日期',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        UNIQUE KEY uk_stock_code (stock_code),
        INDEX idx_industry (industry)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='股票基础信息表';
    """,
    
    # 财务指标表
    """
    CREATE TABLE IF NOT EXISTS finance_indicator (
        id BIGINT AUTO_INCREMENT PRIMARY KEY,
        stock_code VARCHAR(10) NOT NULL COMMENT '股票代码',
        report_date DATE COMMENT '报告期',
        pe_ttm DECIMAL(10, 4) COMMENT '市盈率TTM',
        pb DECIMAL(10, 4) COMMENT '市净率',
        ps_ttm DECIMAL(10, 4) COMMENT '市销率TTM',
        roe DECIMAL(8, 4) COMMENT '净资产收益率(%)',
        roe_diluted DECIMAL(8, 4) COMMENT 'ROE(扣非)(%)',
        gross_margin DECIMAL(8, 4) COMMENT '毛利率(%)',
        net_margin DECIMAL(8, 4) COMMENT '净利率(%)',
        revenue_growth DECIMAL(8, 4) COMMENT '营收增长率(%)',
        profit_growth DECIMAL(8, 4) COMMENT '净利润增长率(%)',
        debt_ratio DECIMAL(8, 4) COMMENT '资产负债率(%)',
        current_ratio DECIMAL(8, 4) COMMENT '流动比率',
        dividend_yield DECIMAL(8, 4) COMMENT '股息率(%)',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        UNIQUE KEY uk_stock_report (stock_code, report_date),
        INDEX idx_stock_code (stock_code)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='财务指标表';
    """,
    
    # 选股结果表
    """
    CREATE TABLE IF NOT EXISTS selection_result (
        id BIGINT AUTO_INCREMENT PRIMARY KEY,
        stock_code VARCHAR(10) NOT NULL COMMENT '股票代码',
        stock_name VARCHAR(50) COMMENT '股票名称',
        select_date DATE NOT NULL COMMENT '选股日期',
        technical_score DECIMAL(5, 2) COMMENT '技术面评分',
        fundamental_score DECIMAL(5, 2) COMMENT '基本面评分',
        sentiment_score DECIMAL(5, 2) COMMENT '情绪面评分',
        total_score DECIMAL(5, 2) NOT NULL COMMENT '总评分',
        ma_trend VARCHAR(20) COMMENT '均线趋势: bullish/bearish/neutral',
        bias DECIMAL(8, 4) COMMENT '乖离率',
        macd_signal VARCHAR(20) COMMENT 'MACD信号: golden_cross/death_cross/others',
        volume_signal VARCHAR(20) COMMENT '量能信号: expansion/contraction/normal',
        select_reason TEXT COMMENT '选股理由',
        is_valid TINYINT(1) DEFAULT 1 COMMENT '是否有效',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_select_date (select_date),
        INDEX idx_stock_code (stock_code),
        INDEX idx_total_score (total_score),
        INDEX idx_valid_date (is_valid, select_date)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='选股结果表';
    """,
    
    # 持仓表
    """
    CREATE TABLE IF NOT EXISTS positions (
        id BIGINT AUTO_INCREMENT PRIMARY KEY,
        stock_code VARCHAR(10) NOT NULL COMMENT '股票代码',
        stock_name VARCHAR(50) COMMENT '股票名称',
        hold_qty INT NOT NULL DEFAULT 0 COMMENT '持仓数量',
        available_qty INT NOT NULL DEFAULT 0 COMMENT '可用数量',
        avg_cost DECIMAL(10, 4) COMMENT '平均成本',
        current_price DECIMAL(10, 4) COMMENT '当前价格',
        market_value DECIMAL(15, 4) COMMENT '市值',
        profit_loss DECIMAL(15, 4) COMMENT '浮动盈亏',
        profit_loss_pct DECIMAL(8, 4) COMMENT '盈亏比例(%)',
        buy_date DATE COMMENT '买入日期',
        stop_loss_price DECIMAL(10, 4) COMMENT '止损价',
        take_profit_price DECIMAL(10, 4) COMMENT '止盈价',
        strategy VARCHAR(50) COMMENT '策略名称',
        status VARCHAR(20) DEFAULT 'holding' COMMENT '状态: holding/sold',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        UNIQUE KEY uk_stock_status (stock_code, status),
        INDEX idx_status (status)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='持仓表';
    """,
    
    # 交易记录表
    """
    CREATE TABLE IF NOT EXISTS trade_history (
        id BIGINT AUTO_INCREMENT PRIMARY KEY,
        stock_code VARCHAR(10) NOT NULL COMMENT '股票代码',
        stock_name VARCHAR(50) COMMENT '股票名称',
        trade_date DATE NOT NULL COMMENT '交易日期',
        trade_time TIME COMMENT '交易时间',
        trade_type VARCHAR(10) NOT NULL COMMENT '交易类型: buy/sell',
        qty INT NOT NULL COMMENT '交易数量',
        price DECIMAL(10, 4) NOT NULL COMMENT '交易价格',
        amount DECIMAL(15, 4) NOT NULL COMMENT '交易金额',
        commission DECIMAL(10, 4) DEFAULT 0 COMMENT '佣金',
        stamp_tax DECIMAL(10, 4) DEFAULT 0 COMMENT '印花税',
        transfer_fee DECIMAL(10, 4) DEFAULT 0 COMMENT '过户费',
        total_cost DECIMAL(15, 4) COMMENT '总成本',
        strategy VARCHAR(50) COMMENT '触发策略',
        order_id VARCHAR(50) COMMENT '委托编号',
        remark TEXT COMMENT '备注',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_trade_date (trade_date),
        INDEX idx_stock_code (stock_code),
        INDEX idx_trade_type (trade_type)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='交易记录表';
    """,
    
    # 资金账户表
    """
    CREATE TABLE IF NOT EXISTS account (
        id BIGINT AUTO_INCREMENT PRIMARY KEY,
        total_asset DECIMAL(15, 4) DEFAULT 0 COMMENT '总资产',
        available_cash DECIMAL(15, 4) DEFAULT 0 COMMENT '可用资金',
        frozen_cash DECIMAL(15, 4) DEFAULT 0 COMMENT '冻结资金',
        market_value DECIMAL(15, 4) DEFAULT 0 COMMENT '股票市值',
        total_profit DECIMAL(15, 4) DEFAULT 0 COMMENT '累计盈亏',
        update_date DATE COMMENT '更新日期',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='资金账户表';
    """
]


def init_database():
    """初始化数据库"""
    print("开始初始化数据库...")
    
    engine = get_engine()
    
    with engine.connect() as conn:
        for sql in TABLES_SQL:
            try:
                conn.execute(text(sql))
                conn.commit()
            except Exception as e:
                print(f"建表失败: {e}")
                raise
    
    print("数据库初始化完成！")
    print("\n已创建表:")
    print("  - kline_daily: 日K线数据")
    print("  - suspend_info: 停复牌信息")
    print("  - stock_basic: 股票基础信息")
    print("  - finance_indicator: 财务指标")
    print("  - selection_result: 选股结果")
    print("  - positions: 持仓")
    print("  - trade_history: 交易记录")
    print("  - account: 资金账户")


if __name__ == '__main__':
    init_database()
