// 简单的API测试工具
const API_BASE = 'http://localhost:8000'

// 测试验证码生成
async function testCaptcha() {
  console.log('🧪 测试验证码生成...')
  const response = await fetch(`${API_BASE}/auth/captcha`)
  const data = await response.json()
  console.log('✅ 验证码生成成功:', data)
  return data
}

// 测试用户注册
async function testRegister() {
  console.log('🧪 测试用户注册...')
  const captcha = await testCaptcha()

  const response = await fetch(`${API_BASE}/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      username: 'testuser',
      email: 'test@example.com',
      password: 'test12345',
      captcha_id: captcha.captcha_id,
      captcha: captcha.captcha_text
    })
  })

  if (response.ok) {
    const data = await response.json()
    console.log('✅ 用户注册成功:', data)
    return data
  } else {
    const error = await response.json()
    console.log('❌ 用户注册失败:', error)
    return null
  }
}

// 测试用户登录
async function testLogin() {
  console.log('🧪 测试用户登录...')
  const captcha = await testCaptcha()

  const response = await fetch(`${API_BASE}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      identifier: 'testuser',
      password: 'test12345',
      captcha_id: captcha.captcha_id,
      captcha: captcha.captcha_text
    })
  })

  if (response.ok) {
    const data = await response.json()
    console.log('✅ 用户登录成功:', data)
    return data
  } else {
    const error = await response.json()
    console.log('❌ 用户登录失败:', error)
    return null
  }
}

// 运行所有测试
async function runTests() {
  console.log('🚀 开始API测试...\n')

  await testCaptcha()
  await testRegister()
  await testLogin()

  console.log('\n🏁 测试完成')
}

// 如果在浏览器环境中运行
if (typeof window !== 'undefined') {
  window.testAPI = { testCaptcha, testRegister, testLogin, runTests }
}

// 如果在Node.js环境中运行
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { testCaptcha, testRegister, testLogin, runTests }
}
