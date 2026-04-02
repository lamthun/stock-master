# -*- coding: utf-8 -*-
"""
交易执行脚本
根据评分结果执行买卖

用法:
    # 模拟交易（默认）
    python execute_trade.py --dry-run
    
    # 查看交易计划
    python execute_trade.py --plan
    
    # 实盘交易（危险！）
    python execute_trade.py --live
"""
import argparse
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
from datetime import datetime, date
from sqlalchemy import text

from db import get_engine


def get_buy_candidates(engine, select_date=None, min_score=70):
    """获取买入候选"""
    if select_date:
        query = """
            SELECT * FROM selection_result 
            WHERE select_date = %s AND decision = 'buy' AND total_score >= %s
            ORDER BY total_score DESC
        """
        df = pd.read_sql(text(query), engine, params=(select_date, min_score))
    else:
        query = """
            SELECT * FROM selection_result 
            WHERE select_date = (SELECT MAX(select_date) FROM selection_result)
            AND decision = 'buy' AND total_score >= %s
            ORDER BY total_score DESC
        """
        df = pd.read_sql(text(query), engine, params=(min_score,))
    
    return df


def get_positions(engine):
    """获取当前持仓"""
    query = "SELECT * FROM positions WHERE status = 'holding'"
    return pd.read_sql(text(query), engine)


def check_sell_signal(positions, engine):
    """检查卖出信号"""
    sell_list = []
    
    for _, pos in positions.iterrows():
        code = pos['stock_code']
        
        # 1. 止损检查
        if pos['current_price'] <= pos['stop_loss_price']:
            sell_list.append({
                'stock_code': code,
                'reason': f"触发止损 (成本{pos['avg_cost']:.2f}, 现价{pos['current_price']:.2f})",
                'qty': pos['hold_qty'],
                'urgency': 'high'
            })
            continue
        
        # 2. 止盈检查
        if pos['current_price'] >= pos['take_profit_price']:
            sell_list.append({
                'stock_code': code,
                'reason': f"触发止盈 ({pos['profit_loss_pct']:.2f}%)",
                'qty': pos['hold_qty'],
                'urgency': 'normal'
            })
            continue
        
        # 3. 评分恶化检查
        query = """
            SELECT decision FROM selection_result 
            WHERE stock_code = %s 
            ORDER BY select_date DESC LIMIT 1
        """
        result = pd.read_sql(text(query), engine, params=(code,))
        
        if not result.empty and result.iloc[0]['decision'] == 'sell':
            sell_list.append({
                'stock_code': code,
                'reason': f"评分恶化，建议离场",
                'qty': pos['hold_qty'],
                'urgency': 'normal'
            })
    
    return sell_list


def generate_trade_plan(buy_candidates, positions, engine, max_positions=10):
    """生成交易计划"""
    plan = {
        'sell': [],
        'buy': [],
        'hold': []
    }
    
    # 检查卖出
    if not positions.empty:
        sell_signals = check_sell_signal(positions, engine)
        plan['sell'] = sell_signals
    
    # 检查买入
    current_holdings = len(positions) if not positions.empty else 0
    available_slots = max_positions - current_holdings + len(plan['sell'])
    
    if available_slots > 0:
        for _, candidate in buy_candidates.head(available_slots).iterrows():
            plan['buy'].append({
                'stock_code': candidate['stock_code'],
                'score': candidate['total_score'],
                'reason': f"综合评分{candidate['total_score']:.1f}",
                'suggested_price': 0,  # 需要实时行情
                'position_pct': 0.1 if candidate['total_score'] >= 80 else 0.05
            })
    
    # 持仓列表
    if not positions.empty:
        for _, pos in positions.iterrows():
            if code not in [s['stock_code'] for s in plan['sell']]:
                plan['hold'].append({
                    'stock_code': pos['stock_code'],
                    'profit_pct': pos['profit_loss_pct'],
                    'days': (date.today() - pos['buy_date']).days if pos['buy_date'] else 0
                })
    
    return plan


def print_trade_plan(plan):
    """打印交易计划"""
    print("\n" + "="*60)
    print("交易计划")
    print("="*60)
    
    # 卖出
    if plan['sell']:
        print(f"\n【卖出】{len(plan['sell'])}只")
        for item in plan['sell']:
            urgency = "🔴" if item['urgency'] == 'high' else "🟡"
            print(f"  {urgency} {item['stock_code']} {item['qty']}股 - {item['reason']}")
    
    # 买入
    if plan['buy']:
        print(f"\n【买入】{len(plan['buy'])}只")
        for item in plan['buy']:
            print(f"  🟢 {item['stock_code']} 评分{item['score']:.1f} - {item['reason']}")
    
    # 持仓
    if plan['hold']:
        print(f"\n【持仓】{len(plan['hold'])}只")
        for item in plan['hold']:
            print(f"  ⚪ {item['stock_code']} 盈亏{item['profit_pct']:.2f}% 持有{item['days']}天")


def record_trade(stock_code, trade_type, qty, price, strategy='', remark=''):
    """记录交易"""
    engine = get_engine()
    
    data = {
        'stock_code': stock_code,
        'trade_date': date.today(),
        'trade_time': datetime.now().time(),
        'trade_type': trade_type,
        'qty': qty,
        'price': price,
        'amount': qty * price,
        'commission': qty * price * 0.0003,  # 佣金
        'stamp_tax': qty * price * 0.001 if trade_type == 'sell' else 0,  # 印花税
        'strategy': strategy,
        'remark': remark
    }
    
    df = pd.DataFrame([data])
    df.to_sql('trade_history', engine, if_exists='append', index=False)
    print(f"  记录交易: {stock_code} {trade_type} {qty}股 @ {price}")


def main():
    parser = argparse.ArgumentParser(description='交易执行')
    parser.add_argument('--plan', action='store_true', help='只显示计划，不执行')
    parser.add_argument('--dry-run', action='store_true', help='模拟执行')
    parser.add_argument('--live', action='store_true', help='实盘执行（危险！）')
    parser.add_argument('--date', type=str, help='日期 YYYY-MM-DD')
    parser.add_argument('--min-score', type=int, default=70, help='最低买入分数')
    
    args = parser.parse_args()
    
    if not any([args.plan, args.dry_run, args.live]):
        args.plan = True  # 默认只显示计划
    
    engine = get_engine()
    
    # 获取数据
    buy_candidates = get_buy_candidates(engine, args.date, args.min_score)
    positions = get_positions(engine)
    
    print(f"候选股票: {len(buy_candidates)}只")
    print(f"当前持仓: {len(positions)}只")
    
    # 生成计划
    plan = generate_trade_plan(buy_candidates, positions, engine)
    print_trade_plan(plan)
    
    # 执行
    if args.live:
        print("\n⚠️  实盘执行！")
        # 这里接入实盘交易API
        # ...
    elif args.dry_run:
        print("\n[模拟执行]")
        for item in plan['sell']:
            record_trade(item['stock_code'], 'sell', item['qty'], 0, remark=item['reason'])
        for item in plan['buy']:
            record_trade(item['stock_code'], 'buy', 100, 0, remark=item['reason'])


if __name__ == '__main__':
    main()
