#!/usr/bin/env python3
"""邮箱配置测试脚本"""

import os
import sys
import smtplib
from email.message import EmailMessage
from email.utils import formataddr
from dotenv import load_dotenv

def load_config():
    """加载SMTP配置"""
    load_dotenv()

    config = {
        'host': os.getenv('SMTP_HOST', 'smtp.qq.com'),
        'port': int(os.getenv('SMTP_PORT', '587')),
        'email': os.getenv('SMTP_EMAIL', ''),
        'password': os.getenv('SMTP_PASSWORD', ''),
        'from_name': os.getenv('SMTP_FROM_NAME', 'Online Judge'),
    }

    return config

def test_smtp_connection(config):
    """测试SMTP连接"""
    print("[测试] SMTP连接测试...")
    print(f"服务器: {config['host']}:{config['port']}")
    print(f"邮箱: {config['email']}")
    print(f"发件人名称: {config['from_name']}")

    try:
        # 测试连接
        if config['port'] == 465:
            print("[连接] 使用SSL连接...")
            with smtplib.SMTP_SSL(config['host'], config['port'], timeout=10) as server:
                server.login(config['email'], config['password'])
                print("[成功] SMTP连接成功！")
                return True
        else:
            print("[连接] 使用TLS连接...")
            with smtplib.SMTP(config['host'], config['port'], timeout=10) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                server.login(config['email'], config['password'])
                print("[成功] SMTP连接成功！")
                return True

    except smtplib.SMTPAuthenticationError as e:
        print(f"[错误] 认证失败: {e}")
        print("[建议] 检查授权码是否正确，不是邮箱密码")
        return False
    except smtplib.SMTPException as e:
        print(f"[错误] SMTP错误: {e}")
        return False
    except Exception as e:
        print(f"[错误] 连接错误: {e}")
        print("[建议] 检查网络连接和防火墙设置")
        return False

def send_test_email(config, test_email=None):
    """发送测试邮件"""
    if not test_email:
        test_email = config['email']

    print(f"\n[测试] 发送测试邮件到: {test_email}")

    try:
        # 创建邮件
        message = EmailMessage()
        message["From"] = formataddr((config['from_name'], config['email']))
        message["To"] = test_email
        message["Subject"] = "【Online Judge】邮箱配置测试"

        # 邮件内容
        html_content = """
        <html>
        <body style="font-family: Arial, sans-serif;">
            <h2 style="color: #e74c3c;">邮箱配置测试成功！</h2>
            <p>如果您收到这封邮件，说明SMTP配置正确。</p>
            <p>现在可以使用邮箱验证码功能了。</p>
            <hr>
            <p style="color: #999; font-size: 12px;">此邮件由系统自动发送，请勿回复。</p>
        </body>
        </html>
        """

        message.set_content(html_content, subtype='html')

        # 发送邮件
        if config['port'] == 465:
            with smtplib.SMTP_SSL(config['host'], config['port'], timeout=15) as server:
                server.login(config['email'], config['password'])
                server.send_message(message)
        else:
            with smtplib.SMTP(config['host'], config['port'], timeout=15) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                server.login(config['email'], config['password'])
                server.send_message(message)

        print("[成功] 测试邮件发送成功！")
        print(f"[提示] 请检查邮箱 {test_email} 是否收到邮件")
        return True

    except Exception as e:
        print(f"[错误] 发送邮件失败: {e}")
        return False

def main():
    """主函数"""
    print("=== Online Judge 邮箱配置测试工具 ===")
    print()

    # 加载配置
    config = load_config()

    # 检查必要配置
    if not config['email'] or not config['password']:
        print("[错误] 缺少必要的邮箱配置")
        print("请在 service/.env 文件中配置以下内容:")
        print("   SMTP_EMAIL=your_email@qq.com")
        print("   SMTP_PASSWORD=your_authorization_code")
        print("   SMTP_HOST=smtp.qq.com")
        print("   SMTP_PORT=587")
        sys.exit(1)

    # 加载配置
    config = load_config()

    # 检查必要配置
    if not config['email'] or not config['password']:
        print("❌ 错误: 缺少必要的邮箱配置")
        print("💡 请在 service/.env 文件中配置以下内容:")
        print("   SMTP_EMAIL=your_email@qq.com")
        print("   SMTP_PASSWORD=your_authorization_code")
        print("   SMTP_HOST=smtp.qq.com")
        print("   SMTP_PORT=587")
        sys.exit(1)

    # 测试连接
    if not test_smtp_connection(config):
        print("\n[失败] SMTP连接测试失败，请检查配置")
        sys.exit(1)

    # 询问是否发送测试邮件
    print("\n" + "=" * 50)
    test_choice = input("是否发送测试邮件？(y/n): ").strip().lower()

    if test_choice == 'y' or test_choice == 'yes':
        custom_email = input("请输入测试邮箱地址 (直接回车使用配置的邮箱): ").strip()

        if custom_email and '@' not in custom_email:
            print("[错误] 无效的邮箱地址")
            sys.exit(1)

        test_email = custom_email if custom_email else config['email']

        if send_test_email(config, test_email):
            print("\n" + "=" * 50)
            print("[完成] 所有测试完成！")
            print("[提示] 如果收到测试邮件，说明邮箱配置完全正确")
        else:
            print("\n[失败] 发送测试邮件失败")
            sys.exit(1)
    else:
        print("\n[成功] 连接测试通过")
        print("[提示] 建议发送测试邮件验证配置是否完全正确")

if __name__ == "__main__":
    main()
