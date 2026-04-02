# -*- coding: utf-8 -*-
"""
基本面选股脚本
基于PE/PB/ROE/成长性等财务指标筛选

用法:
    python select_fundamental.py
    python select_fundamental.py --min-roe 15
    python select_fundamental.py --max-pe 30
"""
import argparse
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
from sqlalchemy import text

from db import get_engine


def calculate_fundamental_score(row):
    """计算基本面得分"""
    score = 50
    reasons = []
    
    pe = row.get('pe_ttm', 0)
    pb = row.get('pb', 0)
    roe = row.get('roe', 0)
    profit_growth = row.get('profit_growth', 0)
    gross_margin = row.get('gross_margin', 0)
    debt_ratio = row.get('debt_ratio', 0)
    
    # PE评分 (低PE加分)
    if 0 < pe < 20:
        score += 15
        reasons.append(f'低PE({pe:.1f})')
    elif 20 <= pe < 40:
        score += 10
    elif pe > 100 or pe < 0:
        score -= 10
    
    # PB评分
    if 0 < pb < 2:
        score += 10
        reasons.append(f'低PB({pb:.1f})')
    elif pb > 10:
        score -= 5
    
    # ROE评分
    if roe > 20:
        score += 15
        reasons.append(f'高ROE({roe:.1f}%)')
    elif roe > 15:
        score += 10
    elif roe < 5:
        score -= 10
    
    # 成长性
    if profit_growth > 50:
        score += 15
        reasons.append(f'高增长({profit_growth:.1f}%)')
    elif profit_growth > 30:
        score += 10
    elif profit_growth > 10:
        score += 5
    elif profit_growth < -20:
        score -= 10
    
    # 毛利率
    if gross_margin > 40:
        score += 10
    elif gross_margin > 30:
        score += 5
    
    # 负债率
    if debt_ratio < 40:
        score += 5
    elif debt_ratio > 70:
        score -= 5
        reasons.append('高负债')
    
    return min(100, max(0, score)), reasons


def main():
    parser = argparse.ArgumentParser(description='基本面选股')
    parser.add_argument('--min-roe', type=float, default=8, help='最低ROE')
    parser.add_argument('--max-pe', type=float, default=100, help='最高PE')
    parser.add_argument('--min-score', type=int, default=60, help='最低基本面分')
    parser.add_argument('--top-n', type=int, default=50, help='取前N只')
    
    args = parser.parse_args()
    
    engine = get_engine()
    
    print(f"筛选条件: ROE>={args.min_roe}%, PE<={args.max_pe}, 最低分{args.min_score}")
    
    # 读取财务数据
    query = """
        SELECT f.*, s.stock_name 
        FROM finance_indicator f
        LEFT JOIN stock_basic s ON f.stock_code = s.stock_code
        WHERE f.pe_ttm > 0 AND f.pe_ttm <= %s AND f.roe >= %s
        ORDER BY f.report_date DESC
    """
    df = pd.read_sql(text(query), engine, params=(args.max_pe, args.min_roe))
    
    if df.empty:
        print("无符合基本条件的股票")
        return
    
    # 去重，保留最新记录
    df = df.drop_duplicates('stock_code', keep='first')
    
    # 计算得分
    results = []
    for _, row in df.iterrows():
        score, reasons = calculate_fundamental_score(row)
        
        if score >= args.min_score:
            results.append({
                'stock_code': row['stock_code'],
                'stock_name': row.get('stock_name', ''),
                'fundamental_score': score,
                'pe_ttm': row.get('pe_ttm'),
                'pb': row.get('pb'),
                'roe': row.get('roe'),
                'profit_growth': row.get('profit_growth'),
                'reason': '; '.join(reasons)
            })
    
    # 排序
    results.sort(key=lambda x: x['fundamental_score'], reverse=True)
    results = results[:args.top_n]
    
    print(f"\n选出 {len(results)} 只股票:")
    print("-" * 80)
    print(f"{'代码':<10} {'名称':<10} {'基本面分':<8} {'PE':<8} {'ROE':<8} {'理由':<20}")
    print("-" * 80)
    
    for r in results:
        print(f"{r['stock_code']:<10} {r['stock_name']:<10} {r['fundamental_score']:<8.1f} "
              f"{r['pe_ttm']:<8.1f} {r['roe']:<8.1f} {r['reason'][:20]:<20}")


if __name__ == '__main__':
    main()
