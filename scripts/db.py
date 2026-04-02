# -*- coding: utf-8 -*-
"""
数据库连接工具
被其他脚本共用
"""
import os
from sqlalchemy import create_engine
from dotenv import load_dotenv

# 加载环境变量
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))


def get_engine():
    """获取数据库引擎"""
    host = os.getenv('MYSQL_HOST', 'localhost')
    port = os.getenv('MYSQL_PORT', '3306')
    user = os.getenv('MYSQL_USER', 'root')
    password = os.getenv('MYSQL_PASSWORD', '')
    database = os.getenv('MYSQL_DATABASE', 'stock_master')
    
    connection_string = f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}?charset=utf8mb4"
    return create_engine(connection_string, pool_pre_ping=True)
