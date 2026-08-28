#!/usr/bin/env python3
"""
密码哈希生成工具

用于生成管理员密码的 bcrypt 哈希值，可直接插入数据库。
"""

import bcrypt
import secrets
import getpass


def generate_password_hash(password: str = None) -> str:
    """生成密码哈希"""
    if password is None:
        password = getpass.getpass("请输入密码: ")
        confirm = getpass.getpass("确认密码: ")
        if password != confirm:
            print("❌ 密码不匹配")
            return None

    # 生成 bcrypt 哈希 (轮数=12，与应用配置一致)
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def generate_jwt_secret() -> str:
    """生成 JWT 密钥"""
    return secrets.token_urlsafe(48)


def main():
    print("=" * 50)
    print("OJ 在线判题系统 - 密码哈希生成工具")
    print("=" * 50)
    print()

    # 选项菜单
    print("请选择功能:")
    print("1. 生成密码哈希")
    print("2. 生成 JWT_SECRET")
    print("3. 同时生成上述两项")
    print()

    choice = input("请输入选项 (1/2/3): ").strip()

    if choice == "1":
        print("\n--- 生成密码哈希 ---")
        hashed = generate_password_hash()
        if hashed:
            print(f"\n✅ 密码哈希生成成功:")
            print(f"   {hashed}")
            print(f"\n💡 插入数据库示例:")
            print(f"   UPDATE users SET hashed_password = '{hashed}' WHERE username = 'admin';")

    elif choice == "2":
        print("\n--- 生成 JWT_SECRET ---")
        secret = generate_jwt_secret()
        print(f"\n✅ JWT_SECRET 生成成功:")
        print(f"   {secret}")
        print(f"\n💡 添加到 .env 文件:")
        print(f"   JWT_SECRET={secret}")

    elif choice == "3":
        print("\n--- 生成密码哈希 ---")
        hashed = generate_password_hash()
        if hashed:
            print(f"\n✅ 密码哈希: {hashed}")

        print("\n--- 生成 JWT_SECRET ---")
        secret = generate_jwt_secret()
        print(f"\n✅ JWT_SECRET: {secret}")

        print("\n" + "=" * 50)
        print("📝 完整配置示例:")
        print("=" * 50)
        print(f"# .env 文件配置")
        print(f"DATABASE_URL=postgresql+asyncpg://...")
        print(f"JWT_SECRET={secret}")
        print(f"ENV=prod")
        print()
        print(f"# SQL 插入管理员用户")
        print(f"INSERT INTO users (username, email, hashed_password, user_number, is_admin)")
        print(f"VALUES ('admin', 'admin@example.com', '{hashed}', 1, true);")

    else:
        print("❌ 无效的选项")

    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n操作已取消")
    except Exception as e:
        print(f"❌ 发生错误: {e}")