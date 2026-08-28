"""测试登录API"""

import asyncio
import httpx


async def test_login_api():
    """测试完整的登录流程"""
    print("=== 测试登录API ===\n")

    try:
        async with httpx.AsyncClient() as client:
            # 1. 获取验证码
            print("1. 获取验证码...")
            captcha_response = await client.get("http://localhost:8000/auth/captcha")
            print(f"   验证码API状态: {captcha_response.status_code}")

            if captcha_response.status_code != 200:
                print(f"   验证码获取失败: {captcha_response.text}")
                return False

            captcha_data = captcha_response.json()
            captcha_id = captcha_data.get("captcha_id")
            captcha_text = captcha_data.get("captcha_text")
            print(f"   验证码ID: {captcha_id}")
            print(f"   验证码文本: {captcha_text}")

            # 2. 测试登录
            print("\n2. 发送登录请求...")
            login_data = {
                "identifier": "admin",
                "password": "123456",
                "captcha_id": captcha_id,
                "captcha": captcha_text
            }

            print(f"   登录参数: 用户名={login_data['identifier']}, 验证码={login_data['captcha']}")
            login_response = await client.post(
                "http://localhost:8000/auth/login",
                json=login_data
            )
            print(f"   登录API状态: {login_response.status_code}")

            if login_response.status_code == 200:
                result = login_response.json()
                print(f"   登录成功!")
                print(f"   访问令牌: {result.get('access_token', 'N/A')[:20]}...")
                print(f"   刷新令牌: {result.get('refresh_token', 'N/A')[:20]}...")
                return True
            else:
                print(f"   登录失败: {login_response.text}")
                return False

    except Exception as e:
        print(f"❌ API测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_user_info_api():
    """测试获取用户信息API"""
    print("\n=== 测试用户信息API ===\n")

    try:
        async with httpx.AsyncClient() as client:
            # 首先登录获取token
            captcha_response = await client.get("http://localhost:8000/auth/captcha")
            captcha_data = captcha_response.json()

            login_response = await client.post(
                "http://localhost:8000/auth/login",
                json={
                    "identifier": "admin",
                    "password": "123456",
                    "captcha_id": captcha_data.get("captcha_id"),
                    "captcha": captcha_data.get("captcha_text")
                }
            )

            if login_response.status_code != 200:
                print("登录失败，无法测试用户信息API")
                return False

            token_data = login_response.json()
            access_token = token_data.get("access_token")

            # 测试获取用户信息
            print("获取当前用户信息...")
            headers = {"Authorization": f"Bearer {access_token}"}
            user_response = await client.get(
                "http://localhost:8000/auth/me",
                headers=headers
            )
            print(f"用户信息API状态: {user_response.status_code}")

            if user_response.status_code == 200:
                user_data = user_response.json()
                print("用户信息获取成功:")
                print(f"  用户名: {user_data.get('username')}")
                print(f"  邮箱: {user_data.get('email')}")
                print(f"  用户编号: {user_data.get('user_number')}")
                print(f"  超级管理员: {user_data.get('is_super_admin')}")
                return True
            else:
                print(f"获取用户信息失败: {user_response.text}")
                return False

    except Exception as e:
        print(f"❌ 用户信息API测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """主函数"""
    print("开始测试登录API...\n")

    # 测试登录API
    login_ok = await test_login_api()

    # 如果登录成功，测试用户信息API
    if login_ok:
        await test_user_info_api()

    print(f"\n=== 测试总结 ===")
    if login_ok:
        print("登录功能: 正常 OK")
    else:
        print("登录功能: 失败 FAIL")


if __name__ == "__main__":
    asyncio.run(main())
