# -*- coding: utf-8 -*-
"""
停复牌数据获取脚本

用法:
    python fetch_suspend.py
    python fetch_suspend.py --date 20240401
"""
import argparse
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import akshare as ak
import pandas as pd
from datetime import datetime

from db import get_engine


def fetch_suspend(date_str=None):
    """获取停牌数据"""
    try:
        df = ak.stock_tfp_em(date=date_str)
        
        if df.empty:
            print("无停牌数据")
            return None
        
        # 标准化列名
        df = df.rename(columns={
            '代码': 'stock_code',
            '名称': 'stock_name',
            '停牌时间': 'suspend_date',
            '预计复牌时间': 'resume_date',
            '停牌原因': 'suspend_reason',
            '市场类型': 'market_type'
        })
        
        df['is_suspended'] = 1
        
        # 转换日期
        df['suspend_date'] = pd.to_datetime(df['suspend_date'], errors='coerce').dt.date
        df['resume_date'] = pd.to_datetime(df['resume_date'], errors='coerce').dt.date
        
        return df
        
    except Exception as e:
        print(f"获取停牌数据失败: {e}")
        return None


def update_resume_stocks(engine):
    """更新已复牌的股票"""
    from sqlalchemy import text
    
    # 将已复牌的股票标记为is_suspended=0
    query = """
        UPDATE suspend_info 
        SET is_suspended = 0, updated_at = NOW()
        WHERE resume_date <= CURDATE() AND is_suspended = 1
    """
    with engine.connect() as conn:
        result = conn.execute(text(query))
        conn.commit()
        if result.rowcount > 0:
            print(f"标记 {result.rowcount} 只股票已复牌")


def main():
    parser = argparse.ArgumentParser(description='获取停复牌数据')
    parser.add_argument('--date', type=str, help='日期 YYYYMMDD，默认今日')
    
    args = parser.parse_args()
    
    print("获取停牌数据...")
    df = fetch_suspend(args.date)
    
    if df is not None and not df.empty:
        engine = get_engine()
        
        # 保存数据
        df.to_sql('suspend_info', engine, if_exists='append', index=False)
        print(f"保存 {len(df)} 条停牌记录")
        
        # 更新已复牌
        update_resume_stocks(engine)


if __name__ == '__main__':
    main()
