#!/usr/bin/env python3
"""测试登录API并显示详细错误"""

import urllib.request
import urllib.error
import json

def test_login():
    """测试登录API"""
    print("=== 测试登录API ===")

    # 先获取验证码
    print("\n1. 获取验证码...")
    try:
        captcha_response = urllib.request.urlopen('http://localhost:8000/auth/captcha')
        captcha_data = json.loads(captcha_response.read().decode())
        print(f"验证码获取成功: {captcha_data}")
    except Exception as e:
        print(f"获取验证码失败: {e}")
        return

    # 测试登录
    print("\n2. 测试登录...")
    login_data = {
        "identifier": "brian_zheng",
        "password": "wrongpassword",  # 故意使用错误密码测试
        "captcha_id": captcha_data["captcha_id"],
        "captcha": captcha_data["captcha_text"]
    }

    print(f"发送登录请求: {login_data}")

    try:
        req = urllib.request.Request(
            'http://localhost:8000/auth/login',
            data=json.dumps(login_data).encode('utf-8'),
            headers={'Content-Type': 'application/json'},
            method='POST'
        )

        response = urllib.request.urlopen(req, timeout=10)
        status_code = response.getcode()
        content = response.read().decode()

        print(f"响应状态码: {status_code}")
        print(f"响应内容: {content}")

        if status_code == 500:
            print("\n[错误] 500内部服务器错误")
            print("这通常表示后端代码抛出了未捕获的异常")
        elif status_code == 401:
            print("\n[正常] 认证失败 - 这是预期的错误")
        else:
            print(f"\n[意外] 状态码: {status_code}")

    except urllib.error.HTTPError as e:
        print(f"[HTTP错误] 状态码: {e.code} - {e.reason}")
        if e.code == 500:
            print("服务器返回500错误，后端代码有问题")
    except Exception as e:
        print(f"[错误] 其他错误: {e}")

if __name__ == "__main__":
    test_login()