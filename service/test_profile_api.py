"""测试用户资料API"""
import asyncio
import httpx

async def test_profile_api():
    async with httpx.AsyncClient() as client:
        # 获取验证码
        captcha_resp = await client.get('http://127.0.0.1:8001/auth/captcha')
        captcha_data = captcha_resp.json()
        print(f'验证码: {captcha_data["captcha_text"]}, ID: {captcha_data["captcha_id"]}')

        # 登录
        login_resp = await client.post('http://127.0.0.1:8001/auth/login', json={
            'identifier': 'testuser',
            'password': 'test123456',
            'captcha': captcha_data['captcha_text'],
            'captcha_id': captcha_data['captcha_id']
        })
        token = login_resp.json()['access_token']
        print(f'登录成功，获取token')

        # 测试获取用户资料
        headers = {'Authorization': f'Bearer {token}'}
        profile_resp = await client.get('http://127.0.0.1:8001/users/me', headers=headers)
        print(f'获取用户资料: {profile_resp.status_code}')
        print(f'用户数据: {profile_resp.json()}')

        # 测试更新用户资料
        update_data = {'bio': '我是算法爱好者'}
        print(f'尝试更新资料: {update_data}')

        update_resp = await client.put(
            'http://127.0.0.1:8001/users/me/profile',
            json=update_data,
            headers=headers
        )
        print(f'更新响应状态: {update_resp.status_code}')
        print(f'更新响应内容: {update_resp.text}')

if __name__ == '__main__':
    asyncio.run(test_profile_api())
