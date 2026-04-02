# -*- coding: utf-8 -*-
"""
综合评分脚本
合并技术面、基本面、资金面评分

用法:
    python score_stocks.py
    python score_stocks.py --date 2024-04-01
    python score_stocks.py --update-db  # 更新数据库
"""
import argparse
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
from datetime import datetime
from sqlalchemy import text

from db import get_engine


def get_latest_selections(engine, select_date=None):
    """获取最新选股结果"""
    if select_date:
        query = """
            SELECT * FROM selection_result 
            WHERE select_date = %s AND is_valid = 1
        """
        df = pd.read_sql(text(query), engine, params=(select_date,))
    else:
        query = """
            SELECT * FROM selection_result 
            WHERE select_date = (SELECT MAX(select_date) FROM selection_result)
            AND is_valid = 1
        """
        df = pd.read_sql(text(query), engine)
    
    return df


def get_fundamental_scores(engine, stock_codes):
    """获取基本面分数"""
    if not stock_codes:
        return {}
    
    placeholders = ','.join(['%s'] * len(stock_codes))
    query = f"""
        SELECT stock_code, pe_ttm, pb, roe, profit_growth
        FROM finance_indicator
        WHERE stock_code IN ({placeholders})
        ORDER BY report_date DESC
    """
    
    df = pd.read_sql(text(query), engine, params=tuple(stock_codes))
    
    # 计算基本面分数
    scores = {}
    for _, row in df.iterrows():
        code = row['stock_code']
        if code in scores:  # 已计算过，跳过
            continue
        
        score = 50
        
        # PE评分
        pe = row.get('pe_ttm', 0)
        if 0 < pe < 20:
            score += 15
        elif 20 <= pe < 40:
            score += 10
        
        # ROE评分
        roe = row.get('roe', 0)
        if roe > 20:
            score += 15
        elif roe > 15:
            score += 10
        
        # 成长性
        growth = row.get('profit_growth', 0)
        if growth > 30:
            score += 10
        elif growth > 10:
            score += 5
        
        scores[code] = min(100, score)
    
    return scores


def calculate_total_score(tech_score, fund_score=50, sentiment_score=50, capital_score=50):
    """计算综合得分"""
    # 权重配置
    tech_weight = 0.40
    fund_weight = 0.30
    sentiment_weight = 0.20
    capital_weight = 0.10
    
    total = (tech_score * tech_weight + 
             fund_score * fund_weight +
             sentiment_score * sentiment_weight +
             capital_score * capital_weight)
    
    return round(total, 2)


def get_decision(total_score):
    """根据分数给出决策"""
    if total_score >= 80:
        return 'buy', 'high'
    elif total_score >= 65:
        return 'buy', 'medium'
    elif total_score >= 50:
        return 'watch', 'medium'
    elif total_score >= 35:
        return 'hold', 'low'
    else:
        return 'sell', 'low'


def main():
    parser = argparse.ArgumentParser(description='综合评分')
    parser.add_argument('--date', type=str, help='日期 YYYY-MM-DD')
    parser.add_argument('--update-db', action='store_true', help='更新数据库')
    parser.add_argument('--min-score', type=int, default=60, help='最低综合分')
    
    args = parser.parse_args()
    
    engine = get_engine()
    
    # 获取选股结果
    df = get_latest_selections(engine, args.date)
    
    if df.empty:
        print("无选股数据，请先运行选股脚本")
        return
    
    print(f"共 {len(df)} 只候选股票")
    
    # 获取基本面分数
    stock_codes = df['stock_code'].tolist()
    fund_scores = get_fundamental_scores(engine, stock_codes)
    
    # 计算综合得分
    results = []
    for _, row in df.iterrows():
        code = row['stock_code']
        
        tech_score = row.get('technical_score', 0)
        fund_score = fund_scores.get(code, 50)
        
        total = calculate_total_score(tech_score, fund_score)
        decision, confidence = get_decision(total)
        
        if total >= args.min_score:
            results.append({
                'stock_code': code,
                'stock_name': row.get('stock_name', ''),
                'select_date': row['select_date'],
                'technical_score': tech_score,
                'fundamental_score': fund_score,
                'total_score': total,
                'decision': decision,
                'confidence': confidence,
                'ma_trend': row.get('ma_trend', ''),
                'bias': row.get('bias', 0)
            })
    
    # 排序
    results.sort(key=lambda x: x['total_score'], reverse=True)
    
    print(f"\n综合评分 >= {args.min_score} 的股票 ({len(results)}只):")
    print("-" * 70)
    print(f"{'代码':<10} {'技术':<8} {'基本':<8} {'综合':<8} {'决策':<8} {'置信':<8}")
    print("-" * 70)
    
    for r in results:
        print(f"{r['stock_code']:<10} {r['technical_score']:<8.1f} "
              f"{r['fundamental_score']:<8.1f} {r['total_score']:<8.1f} "
              f"{r['decision']:<8} {r['confidence']:<8}")
    
    # 更新数据库
    if args.update_db and results:
        update_query = """
            UPDATE selection_result 
            SET total_score = %s, decision = %s
            WHERE stock_code = %s AND select_date = %s
        """
        with engine.connect() as conn:
            for r in results:
                conn.execute(text(update_query), 
                           (r['total_score'], r['decision'], 
                            r['stock_code'], r['select_date']))
            conn.commit()
        print(f"\n已更新 {len(results)} 条记录")


if __name__ == '__main__':
    main()
