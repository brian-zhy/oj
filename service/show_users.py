#!/usr/bin/env python3
"""查看数据库中的用户信息"""

import sqlite3
import json
from pathlib import Path

def show_users():
    """显示数据库中的用户信息"""
    db_path = Path("service/oj.db")

    if not db_path.exists():
        print("数据库文件不存在")
        return

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # 获取所有表名
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        print("=== 数据库表 ===")
        for table in tables:
            print(f"- {table[0]}")

        # 检查users表是否存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users';")
        if cursor.fetchone():
            print("\n=== 用户表结构 ===")
            cursor.execute("PRAGMA table_info(users);")
            columns = cursor.fetchall()
            for col in columns:
                print(f"- {col[1]} ({col[2]})")

            print("\n=== 用户数据 ===")
            cursor.execute("SELECT id, username, email, phone, user_number, is_active, created_at FROM users;")
            users = cursor.fetchall()

            if users:
                for user in users:
                    print(f"ID: {user[0]}")
                    print(f"用户名: {user[1]}")
                    print(f"邮箱: {user[2]}")
                    print(f"手机: {user[3]}")
                    print(f"用户编号: {user[4]}")
                    print(f"状态: {'激活' if user[5] else '未激活'}")
                    print(f"创建时间: {user[6]}")
                    print("-" * 40)
            else:
                print("数据库中暂无用户数据")
                print("\n=== 注册新用户指南 ===")
                print("1. 访问: http://localhost:5187/register")
                print("2. 填写用户名、邮箱、密码")
                print("3. 点击'获取验证码'按钮")
                print("4. 检查邮箱获取验证码")
                print("5. 输入验证码完成注册")
        else:
            print("数据库中没有users表")
            print("\n请先创建数据库表结构")

        conn.close()

    except sqlite3.Error as e:
        print(f"数据库错误: {e}")

if __name__ == "__main__":
    show_users()