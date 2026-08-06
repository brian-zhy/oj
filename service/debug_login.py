#!/usr/bin/env python3
"""临时测试登录 - 绕过验证码验证"""

import requests

# 这个脚本仅用于调试
def test_login_no_captcha():
    """测试不需要验证码的登录"""
    print("=== 测试登录（无验证码）===")

    # 先获取一个验证码（因为API要求）
    import json
    captcha_response = requests.get('http://localhost:8000/auth/captcha')
    captcha_data = captcha_response.json()

    # 测试你的真实登录
    login_data = {
        "identifier": "brian_zheng",
        "password": "你的真实密码",  # 请替换为实际密码
        "captcha_id": captcha_data["captcha_id"],
        "captcha": captcha_data["captcha_text"]  # 使用正确的验证码
    }

    try:
        response = requests.post(
            'http://localhost:8000/auth/login',
            json=login_data,
            timeout=10
        )
        print(f"状态码: {response.status_code}")
        print(f"响应: {response.text}")

        if response.status_code == 200:
            print("✅ 登录成功!")
            token_data = response.json()
            print(f"Token: {token_data}")
        else:
            print(f"❌ 登录失败: {response.text}")

    except Exception as e:
        print(f"❌ 连接错误: {e}")

if __name__ == "__main__":
    test_login_no_captcha()