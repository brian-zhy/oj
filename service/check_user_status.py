#!/usr/bin/env python3
"""检查用户禁言状态"""

import sqlite3
import json
from pathlib import Path

def check_user_status():
    """检查用户的详细状态"""
    db_path = Path("service/oj.db")

    if not db_path.exists():
        print("数据库文件不存在")
        return

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        print("=== 用户状态检查 ===\n")

        # 检查用户ID为1的用户状态
        cursor.execute("""
            SELECT
                id, username, email, user_number,
                is_active, is_admin, is_banned, is_cheater, can_speak,
                can_manage_users, can_manage_posts,
                created_at
            FROM users WHERE id = 1
        """)

        user = cursor.fetchone()

        if user:
            print(f"用户ID: {user[0]}")
            print(f"用户名: {user[1]}")
            print(f"邮箱: {user[2]}")
            print(f"用户编号: {user[3]}")
            print(f"账户状态: {'[正常]' if user[4] else '[未激活]'}")
            print(f"管理员: {'[是]' if user[5] else '[否]'}")
            print(f"封禁状态: {'[已封禁]' if user[6] else '[未封禁]'}")
            print(f"作弊标记: {'[有作弊记录]' if user[7] else '[无作弊记录]'}")
            print(f"发言权限: {'[禁言]' if not user[8] else '[正常]'}")
            print(f"用户管理权限: {'[有]' if user[9] else '[无]'}")
            print(f"帖子管理权限: {'[有]' if user[10] else '[无]'}")
            print(f"注册时间: {user[11]}")

            print("\n=== 权限分析 ===")
            if not user[8]:  # can_speak = false
                print("[警告] 当前用户发言权限被关闭（can_speak = false）")
                print("这可能是因为:")
                print("1. 数据库初始设置错误")
                print("2. 管理员手动禁言")
                print("3. 系统自动禁言")

            print("\n=== 修复建议 ===")
            print("如果您认为这是错误，可以执行:")
            print("UPDATE users SET can_speak = true WHERE id = 1;")
        else:
            print("未找到用户ID为1的用户")

        conn.close()

    except sqlite3.Error as e:
        print(f"数据库错误: {e}")

if __name__ == "__main__":
    check_user_status()