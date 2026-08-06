#!/usr/bin/env python3
"""后端服务连接测试脚本"""

import sys
import subprocess
import time
import requests
from pathlib import Path

def check_backend_running():
    """检查后端服务是否运行"""
    print("=== 后端服务连接测试 ===")

    try:
        # 测试根路径
        response = requests.get("http://localhost:8000/", timeout=5)
        print(f"✅ 后端服务运行中: {response.json()}")
        return True
    except requests.exceptions.ConnectionError:
        print("❌ 后端服务未运行或无法连接")
        print("💡 请先启动后端服务: cd service && uv run uvicorn app.main:app --reload --port 8000")
        return False
    except Exception as e:
        print(f"❌ 连接错误: {e}")
        return False

def test_api_endpoints():
    """测试关键API端点"""
    print("\n=== 测试API端点 ===")

    endpoints = [
        ("GET", "/", "健康检查"),
        ("GET", "/docs", "API文档"),
        ("GET", "/openapi.json", "OpenAPI规范"),
        ("POST", "/auth/send-verification", "发送验证码"),
        ("GET", "/auth/captcha", "图形验证码"),
    ]

    for method, endpoint, description in endpoints:
        try:
            if method == "GET":
                response = requests.get(f"http://localhost:8000{endpoint}", timeout=5)
            else:
                response = requests.post(f"http://localhost:8000{endpoint}", timeout=5)

            if response.status_code < 400:
                print(f"✅ {method} {endpoint} ({description}) - 状态码: {response.status_code}")
            else:
                print(f"⚠️  {method} {endpoint} ({description}) - 状态码: {response.status_code}")
        except requests.exceptions.ConnectionError:
            print(f"❌ {method} {endpoint} ({description}) - 连接失败")
        except Exception as e:
            print(f"❌ {method} {endpoint} ({description}) - 错误: {e}")

def test_cors():
    """测试CORS配置"""
    print("\n=== CORS配置测试 ===")

    try:
        response = requests.get(
            "http://localhost:8000/",
            headers={"Origin": "http://localhost:5187"},
            timeout=5
        )

        cors_headers = {
            "Access-Control-Allow-Origin": response.headers.get("Access-Control-Allow-Origin"),
            "Access-Control-Allow-Methods": response.headers.get("Access-Control-Allow-Methods"),
            "Access-Control-Allow-Headers": response.headers.get("Access-Control-Allow-Headers"),
        }

        print("CORS响应头:")
        for header, value in cors_headers.items():
            if value:
                print(f"✅ {header}: {value}")
            else:
                print(f"❌ {header}: 未设置")

        if cors_headers["Access-Control-Allow-Origin"]:
            print("\n✅ CORS配置正确，前端可以正常调用API")
        else:
            print("\n⚠️  CORS可能有问题")

    except Exception as e:
        print(f"❌ CORS测试失败: {e}")

def main():
    """主函数"""
    print("🚀 Online Judge 后端服务连接测试\n")

    # 检查后端服务
    if not check_backend_running():
        print("\n请启动后端服务后重新运行此测试")
        sys.exit(1)

    # 测试API端点
    test_api_endpoints()

    # 测试CORS
    test_cors()

    print("\n=== 测试完成 ===")
    print("💡 如果所有测试都通过，前端应该可以正常连接后端")
    print("💡 如果仍有问题，请检查浏览器控制台的错误信息")

if __name__ == "__main__":
    main()