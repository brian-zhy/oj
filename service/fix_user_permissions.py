#!/usr/bin/env python3
"""修复用户发言权限"""

import sqlite3
from pathlib import Path

def fix_user_permissions():
    """修复用户的发言权限"""
    db_path = Path("service/oj.db")

    if not db_path.exists():
        print("数据库文件不存在")
        return False

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        print("=== 修复用户权限 ===\n")

        # 查看当前状态
        cursor.execute("SELECT id, username, can_speak FROM users WHERE id = 1")
        user = cursor.fetchone()

        if user:
            print(f"修复前状态: {user[1]} - can_speak = {user[2]}")

            # 修复发言权限
            cursor.execute("UPDATE users SET can_speak = true WHERE id = 1")
            conn.commit()

            # 验证修复结果
            cursor.execute("SELECT id, username, can_speak FROM users WHERE id = 1")
            fixed_user = cursor.fetchone()

            print(f"修复后状态: {fixed_user[1]} - can_speak = {fixed_user[2]}")

            if fixed_user[2]:
                print("\n[成功] 发言权限已修复!")
                print("现在您可以正常发言和参与讨论了。")
                return True
            else:
                print("\n[失败] 修复失败，请检查数据库")
                return False
        else:
            print("未找到用户")
            return False

        conn.close()

    except sqlite3.Error as e:
        print(f"数据库错误: {e}")
        return False

if __name__ == "__main__":
    success = fix_user_permissions()
    exit(0 if success else 1)