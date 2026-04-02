# -*- coding: utf-8 -*-
"""
财务指标获取脚本

用法:
    python fetch_finance.py --code 000001
    python fetch_finance.py --all
"""
import argparse
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import akshare as ak
import pandas as pd
from tqdm import tqdm

from db import get_engine


def fetch_single_finance(stock_code):
    """获取单只股票财务指标"""
    try:
        code = stock_code.strip().split('.')[0]
        
        # 个股指标
        df_indicator = ak.stock_a_indicator_lg(symbol=code)
        
        # 主要财务指标
        df_finance = ak.stock_financial_analysis_indicator(symbol=code)
        
        # 合并数据
        result = {}
        
        if not df_indicator.empty:
            row = df_indicator.iloc[0]
            result['pe_ttm'] = float(row.get('市盈率', 0) or 0)
            result['pb'] = float(row.get('市净率', 0) or 0)
            result['ps_ttm'] = float(row.get('市销率', 0) or 0)
            result['dividend_yield'] = float(row.get('股息率', 0) or 0)
        
        if not df_finance.empty:
            row = df_finance.iloc[0]
            result['roe'] = float(row.get('净资产收益率', 0) or 0)
            result['roe_diluted'] = float(row.get('净资产收益率(扣非)', 0) or 0)
            result['gross_margin'] = float(row.get('销售毛利率', 0) or 0)
            result['net_margin'] = float(row.get('销售净利率', 0) or 0)
            result['debt_ratio'] = float(row.get('资产负债率', 0) or 0)
            result['current_ratio'] = float(row.get('流动比率', 0) or 0)
        
        result['stock_code'] = code
        result['report_date'] = pd.Timestamp.now().date()
        
        return result
        
    except Exception as e:
        print(f"{stock_code} 获取失败: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(description='获取财务指标')
    parser.add_argument('--code', type=str, help='股票代码，多个用逗号分隔')
    parser.add_argument('--all', action='store_true', help='获取所有股票')
    parser.add_argument('--limit', type=int, default=100, help='限制数量')
    
    args = parser.parse_args()
    
    if args.code:
        codes = [c.strip() for c in args.code.split(',')]
    elif args.all:
        try:
            df = ak.stock_zh_a_spot_em()
            codes = df['代码'].tolist()[:args.limit]
        except Exception as e:
            print(f"获取股票列表失败: {e}")
            return
    else:
        print("请指定 --code 或 --all")
        return
    
    print(f"共 {len(codes)} 只股票")
    
    engine = get_engine()
    results = []
    
    for code in tqdm(codes, desc="获取财务数据"):
        data = fetch_single_finance(code)
        if data:
            results.append(data)
    
    if results:
        df = pd.DataFrame(results)
        df.to_sql('finance_indicator', engine, if_exists='append', index=False)
        print(f"保存 {len(results)} 条财务记录")


if __name__ == '__main__':
    main()
