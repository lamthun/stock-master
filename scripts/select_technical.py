# -*- coding: utf-8 -*-
"""
技术面选股脚本
基于均线、MACD、量价等技术指标选股

用法:
    python select_technical.py
    python select_technical.py --date 2024-04-01
    python select_technical.py --min-score 70
    python select_technical.py --ma-bullish  # 只看均线多头
"""
import argparse
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
from datetime import datetime, timedelta
from sqlalchemy import text

from db import get_engine


def get_latest_trade_date(engine):
    """获取最新交易日期"""
    query = "SELECT MAX(trade_date) as max_date FROM kline_daily"
    df = pd.read_sql(text(query), engine)
    return df.iloc[0]['max_date']


def get_stock_kline(engine, stock_code, trade_date, days=60):
    """获取股票K线数据"""
    query = """
        SELECT * FROM kline_daily 
        WHERE stock_code = %s AND trade_date <= %s
        ORDER BY trade_date DESC
        LIMIT %s
    """
    df = pd.read_sql(text(query), engine, params=(stock_code, trade_date, days))
    return df.sort_values('trade_date')


def analyze_ma_trend(df):
    """分析均线趋势"""
    if len(df) < 2:
        return 'neutral', 0
    
    latest = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 1 else latest
    
    # 均线多头排列: MA5 > MA10 > MA20 > MA60
    ma_bullish = (latest['ma5'] > latest['ma10'] > latest['ma20'] > latest['ma60'])
    
    # 均线空头排列
    ma_bearish = (latest['ma5'] < latest['ma10'] < latest['ma20'] < latest['ma60'])
    
    if ma_bullish:
        return 'bullish', 25
    elif ma_bearish:
        return 'bearish', -20
    
    # 判断是否处于上升趋势
    if latest['ma5'] > latest['ma20'] and latest['close_price'] > latest['ma20']:
        return 'weak_bullish', 15
    
    return 'neutral', 0


def analyze_macd(df):
    """分析MACD信号"""
    if len(df) < 2:
        return 'none', 0
    
    latest = df.iloc[-1]
    prev = df.iloc[-2]
    
    # 金叉: DIF上穿DEA
    golden_cross = (prev['macd_dif'] < prev['macd_dea'] and 
                    latest['macd_dif'] > latest['macd_dea'])
    
    # 死叉
    death_cross = (prev['macd_dif'] > prev['macd_dea'] and 
                   latest['macd_dif'] < latest['macd_dea'])
    
    if golden_cross:
        return 'golden_cross', 20
    elif death_cross:
        return 'death_cross', -15
    
    # MACD柱状体向上
    if latest['macd_hist'] > prev['macd_hist'] and latest['macd_hist'] > 0:
        return 'positive_expanding', 10
    
    return 'none', 0


def analyze_volume(df):
    """分析成交量"""
    if len(df) < 5:
        return 'normal', 0
    
    latest = df.iloc[-1]
    avg_vol = df['volume'].tail(5).mean()
    
    # 放量 (>1.5倍均量)
    if latest['volume'] > avg_vol * 1.5:
        return 'expansion', 10
    
    # 缩量
    if latest['volume'] < avg_vol * 0.7:
        return 'contraction', -5
    
    return 'normal', 0


def analyze_bias(df, threshold=5):
    """分析乖离率"""
    latest = df.iloc[-1]
    bias = latest.get('bias', 0)
    
    # 乖离率过高，不追高
    if bias > threshold:
        return 'overbought', -15
    
    # 负乖离过大，可能反弹
    if bias < -10:
        return 'oversold', 10
    
    return 'normal', 0


def analyze_support_resistance(df):
    """分析支撑阻力"""
    if len(df) < 20:
        return 'none', 0
    
    latest = df.iloc[-1]
    close = latest['close_price']
    
    # 近20日高低点
    high_20 = df['high_price'].tail(20).max()
    low_20 = df['low_price'].tail(20).min()
    
    # 突破前高
    if close > high_20 * 0.98 and close < high_20 * 1.02:
        return 'breakout', 15
    
    # 接近前低支撑
    if close < low_20 * 1.05 and close > low_20 * 0.95:
        return 'support', 10
    
    return 'none', 0


def calculate_technical_score(stock_code, engine, trade_date):
    """计算技术得分"""
    df = get_stock_kline(engine, stock_code, trade_date)
    
    if df.empty or len(df) < 20:
        return None
    
    score = 50  # 基础分
    reasons = []
    
    # 均线分析
    ma_trend, ma_score = analyze_ma_trend(df)
    score += ma_score
    if ma_trend == 'bullish':
        reasons.append('均线多头排列')
    elif ma_trend == 'bearish':
        reasons.append('均线空头排列')
    
    # MACD分析
    macd_signal, macd_score = analyze_macd(df)
    score += macd_score
    if macd_signal == 'golden_cross':
        reasons.append('MACD金叉')
    elif macd_signal == 'death_cross':
        reasons.append('MACD死叉')
    
    # 成交量分析
    vol_signal, vol_score = analyze_volume(df)
    score += vol_score
    if vol_signal == 'expansion':
        reasons.append('放量')
    
    # 乖离率分析
    bias_signal, bias_score = analyze_bias(df)
    score += bias_score
    if bias_signal == 'overbought':
        reasons.append('乖离率过高')
    elif bias_signal == 'oversold':
        reasons.append('超卖')
    
    # 支撑阻力
    sr_signal, sr_score = analyze_support_resistance(df)
    score += sr_score
    if sr_signal == 'breakout':
        reasons.append('突破形态')
    elif sr_signal == 'support':
        reasons.append('均线支撑')
    
    latest = df.iloc[-1]
    
    return {
        'stock_code': stock_code,
        'stock_name': '',  # 稍后补充
        'select_date': trade_date,
        'technical_score': min(100, max(0, score)),
        'ma_trend': ma_trend,
        'bias': latest.get('bias', 0),
        'macd_signal': macd_signal,
        'volume_signal': vol_signal,
        'select_reason': '; '.join(reasons),
        'is_valid': 1 if score >= 60 else 0
    }


def get_stock_list(engine, trade_date):
    """获取当日有数据的股票列表"""
    query = """
        SELECT DISTINCT stock_code FROM kline_daily 
        WHERE trade_date = %s
    """
    df = pd.read_sql(text(query), engine, params=(trade_date,))
    return df['stock_code'].tolist()


def main():
    parser = argparse.ArgumentParser(description='技术面选股')
    parser.add_argument('--date', type=str, help='选股日期 YYYY-MM-DD')
    parser.add_argument('--min-score', type=int, default=60, help='最低技术得分')
    parser.add_argument('--ma-bullish', action='store_true', help='只看均线多头')
    parser.add_argument('--limit', type=int, default=100, help='限制分析数量')
    
    args = parser.parse_args()
    
    engine = get_engine()
    
    # 确定日期
    if args.date:
        trade_date = pd.to_datetime(args.date).date()
    else:
        trade_date = get_latest_trade_date(engine)
    
    print(f"选股日期: {trade_date}")
    
    # 获取股票列表
    stock_codes = get_stock_list(engine, trade_date)[:args.limit]
    print(f"共 {len(stock_codes)} 只股票待分析")
    
    # 分析每只股票
    results = []
    for code in stock_codes:
        result = calculate_technical_score(code, engine, trade_date)
        if result:
            # 均线多头筛选
            if args.ma_bullish and result['ma_trend'] != 'bullish':
                continue
            
            # 最低分筛选
            if result['technical_score'] >= args.min_score:
                results.append(result)
    
    # 排序
    results.sort(key=lambda x: x['technical_score'], reverse=True)
    
    print(f"\n选出 {len(results)} 只股票 (最低分 {args.min_score}):")
    print("-" * 60)
    print(f"{'代码':<10} {'技术分':<8} {'趋势':<15} {'乖离率':<8} {'理由':<20}")
    print("-" * 60)
    
    for r in results[:20]:  # 只显示前20
        print(f"{r['stock_code']:<10} {r['technical_score']:<8.1f} "
              f"{r['ma_trend']:<15} {r['bias']:<8.2f} {r['select_reason'][:20]:<20}")
    
    # 保存到数据库
    if results:
        df = pd.DataFrame(results)
        df.to_sql('selection_result', engine, if_exists='append', index=False)
        print(f"\n保存 {len(results)} 条选股结果")


if __name__ == '__main__':
    main()
