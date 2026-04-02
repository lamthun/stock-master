# -*- coding: utf-8 -*-
"""
日K线数据获取脚本
从AkShare获取日K线数据并存入MySQL

用法:
    # 获取单只股票
    python fetch_kline.py --code 000001
    
    # 获取多只股票
    python fetch_kline.py --code 000001,000002,600000
    
    # 获取所有股票
    python fetch_kline.py --all
    
    # 获取指定日期范围
    python fetch_kline.py --code 000001 --start 20240101 --end 20240401
    
    # 获取最近N天
    python fetch_kline.py --code 000001 --days 60
"""
import argparse
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import akshare as ak
import pandas as pd
from datetime import datetime, timedelta
from sqlalchemy import text
from tqdm import tqdm

from db import get_engine


def calc_ma(series, window):
    """计算移动平均线"""
    return series.rolling(window=window).mean()


def calc_macd(close):
    """计算MACD"""
    exp1 = close.ewm(span=12, adjust=False).mean()
    exp2 = close.ewm(span=26, adjust=False).mean()
    dif = exp1 - exp2
    dea = dif.ewm(span=9, adjust=False).mean()
    hist = 2 * (dif - dea)
    return dif, dea, hist


def calc_rsi(close, window=14):
    """计算RSI"""
    delta = close.diff()
    gain = delta.where(delta > 0, 0).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def process_kline(df):
    """处理K线数据，添加技术指标"""
    if df.empty:
        return df
    
    df = df.copy()
    
    # 确保列名统一
    column_map = {
        '日期': 'trade_date',
        '开盘': 'open_price',
        '收盘': 'close_price',
        '最高': 'high_price',
        '最低': 'low_price',
        '成交量': 'volume',
        '成交额': 'amount',
        '振幅': 'amplitude',
        '涨跌幅': 'pct_change',
        '涨跌额': 'change_amount',
        '换手率': 'turnover'
    }
    df = df.rename(columns={k: v for k, v in column_map.items() if k in df.columns})
    
    # 转换日期
    if 'trade_date' in df.columns:
        df['trade_date'] = pd.to_datetime(df['trade_date']).dt.date
    
    # 计算技术指标
    close = df['close_price']
    
    # 移动平均线
    df['ma5'] = calc_ma(close, 5)
    df['ma10'] = calc_ma(close, 10)
    df['ma20'] = calc_ma(close, 20)
    df['ma60'] = calc_ma(close, 60)
    
    # 乖离率
    df['bias'] = (close - df['ma20']) / df['ma20'] * 100
    
    # MACD
    df['macd_dif'], df['macd_dea'], df['macd_hist'] = calc_macd(close)
    
    # RSI
    df['rsi'] = calc_rsi(close)
    
    return df


def fetch_single_stock(stock_code, start_date=None, end_date=None):
    """获取单只股票K线"""
    try:
        # 标准化代码
        code = stock_code.strip().split('.')[0]
        
        # 获取数据
        df = ak.stock_zh_a_hist(symbol=code, period="daily", 
                                start_date=start_date, end_date=end_date,
                                adjust="qfq")
        
        if df.empty:
            print(f"{stock_code}: 无数据")
            return None
        
        # 处理数据
        df = process_kline(df)
        df['stock_code'] = code
        
        return df
        
    except Exception as e:
        print(f"{stock_code} 获取失败: {e}")
        return None


def save_to_mysql(df, engine):
    """保存到MySQL"""
    if df is None or df.empty:
        return 0
    
    try:
        # 使用INSERT IGNORE避免重复
        df.to_sql('kline_daily', engine, if_exists='append', index=False,
                  method='multi', chunksize=1000)
        return len(df)
    except Exception as e:
        print(f"保存失败: {e}")
        return 0


def get_stock_list(market='all'):
    """获取股票列表"""
    try:
        df = ak.stock_zh_a_spot_em()
        
        if market == 'sh':
            df = df[df['代码'].str.startswith('6')]
        elif market == 'sz':
            df = df[df['代码'].str.startswith(('0', '3'))]
        elif market == 'bj':
            df = df[df['代码'].str.startswith('8')]
        
        return df['代码'].tolist()
    except Exception as e:
        print(f"获取股票列表失败: {e}")
        return []


def main():
    parser = argparse.ArgumentParser(description='获取日K线数据')
    parser.add_argument('--code', type=str, help='股票代码，多个用逗号分隔')
    parser.add_argument('--all', action='store_true', help='获取所有股票')
    parser.add_argument('--market', type=str, default='all', 
                       choices=['all', 'sh', 'sz', 'bj'], help='市场')
    parser.add_argument('--start', type=str, help='开始日期 YYYYMMDD')
    parser.add_argument('--end', type=str, help='结束日期 YYYYMMDD')
    parser.add_argument('--days', type=int, default=365, help='获取最近N天')
    parser.add_argument('--limit', type=int, help='限制股票数量')
    
    args = parser.parse_args()
    
    # 计算日期范围
    if args.end:
        end_date = args.end
    else:
        end_date = datetime.now().strftime('%Y%m%d')
    
    if args.start:
        start_date = args.start
    else:
        start_date = (datetime.now() - timedelta(days=args.days)).strftime('%Y%m%d')
    
    print(f"日期范围: {start_date} - {end_date}")
    
    # 获取股票列表
    if args.all:
        stock_codes = get_stock_list(args.market)
        if args.limit:
            stock_codes = stock_codes[:args.limit]
    elif args.code:
        stock_codes = [c.strip() for c in args.code.split(',')]
    else:
        print("请指定 --code 或 --all")
        return
    
    print(f"共 {len(stock_codes)} 只股票")
    
    # 获取数据
    engine = get_engine()
    total_saved = 0
    failed = []
    
    for code in tqdm(stock_codes, desc="获取K线"):
        df = fetch_single_stock(code, start_date, end_date)
        if df is not None:
            count = save_to_mysql(df, engine)
            total_saved += count
        else:
            failed.append(code)
    
    print(f"\n完成！保存 {total_saved} 条K线数据")
    if failed:
        print(f"失败 {len(failed)} 只: {', '.join(failed[:10])}...")


if __name__ == '__main__':
    main()
