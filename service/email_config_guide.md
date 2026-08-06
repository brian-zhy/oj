# 邮箱验证码配置指南

## 概述
本项目使用SMTP协议发送邮箱验证码。如果验证码无法收到，请按照以下步骤检查和配置。

## 配置步骤

### 1. 获取SMTP授权码

#### QQ邮箱
1. 登录QQ邮箱网页版
2. 点击设置 -> 账户
3. 开启"POP3/SMTP服务"
4. 生成授权码（不是QQ密码）
5. 保存授权码

#### 163邮箱
1. 登录163邮箱网页版
2. 点击设置 -> POP3/SMTP/IMAP
3. 开启"SMTP服务"
4. 获取授权码

#### Gmail
1. 开启两步验证
2. 生成应用专用密码
3. 使用应用专用密码作为SMTP密码

### 2. 配置环境变量

编辑 `service/.env` 文件，确保以下配置正确：

```env
# SMTP邮件发送配置
SMTP_HOST=smtp.qq.com
SMTP_PORT=587
SMTP_EMAIL=your_email@qq.com
SMTP_PASSWORD=your_authorization_code
SMTP_FROM_NAME=Online Judge
```

**重要说明：**
- `SMTP_PORT=587` 使用TLS加密
- `SMTP_PORT=465` 使用SSL加密
- `SMTP_PASSWORD` 必须是授权码，不是邮箱密码
- QQ邮箱推荐使用端口587

### 3. 常见端口配置

| 邮箱服务商 | SMTP服务器 | 端口 | 加密方式 |
|------------|-----------|------|----------|
| QQ邮箱 | smtp.qq.com | 587 | TLS |
| QQ邮箱 | smtp.qq.com | 465 | SSL |
| 163邮箱 | smtp.163.com | 465 | SSL |
| Gmail | smtp.gmail.com | 587 | TLS |
| Outlook | smtp.office365.com | 587 | TLS |

## 测试配置

### 1. 启动后端服务
```bash
cd service
uv run python -m uvicorn app.main:app --reload --port 8000
```

### 2. 测试邮箱配置
访问：`http://localhost:8000/auth/email-config-test`

正常返回示例：
```json
{
  "configured": true,
  "smtp_host": "smtp.qq.com",
  "smtp_port": 587,
  "smtp_email": "your_email@qq.com",
  "from_name": "Online Judge",
  "password_set": true
}
```

### 3. 测试发送验证码
使用注册页面测试发送验证码功能。

## 常见问题

### 验证码无法收到
1. **检查垃圾邮件文件夹**
   - 验证码邮件可能被误判为垃圾邮件

2. **检查SMTP配置**
   - 确认授权码正确
   - 确认端口号正确
   - 确认SMTP服务器地址正确

3. **查看后端日志**
   - 启动服务时会显示邮件配置状态
   - 发送验证码时会显示详细日志

### "认证失败"错误
- 授权码错误，重新生成授权码
- 部分邮箱需要使用"应用专用密码"

### "连接超时"错误
- 检查网络连接
- 检查防火墙设置
- 尝试更换端口号（465或587）

### "频率限制"错误
- 邮箱服务商通常限制发送频率
- QQ邮箱：每分钟最多发送40封邮件
- 建议测试时设置适当的间隔时间

## 安全建议

1. **不要提交.env文件到Git**
   - .env文件包含敏感信息
   - 已在.gitignore中排除

2. **使用专用邮箱**
   - 建议使用专门的邮箱发送验证码
   - 不要使用个人主邮箱

3. **定期更换授权码**
   - 定期更换SMTP授权码
   - 如果授权码泄露，立即更换

## 生产环境部署

1. **使用环境变量**
   ```bash
   export SMTP_HOST=smtp.qq.com
   export SMTP_PORT=587
   export SMTP_EMAIL=your_email@qq.com
   export SMTP_PASSWORD=your_authorization_code
   export SMTP_FROM_NAME=Online Judge
   ```

2. **使用专业邮件服务**
   - 考虑使用SendGrid、Mailgun等专业服务
   - 提高邮件送达率
   - 更好的监控和分析

3. **配置Redis存储验证码**
   - 当前使用内存存储
   - 生产环境建议使用Redis
   - 支持分布式部署

## 调试技巧

1. **启用详细日志**
   ```python
   # 在service/app/main.py中添加
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```

2. **检查验证码生成**
   - 查看后端日志中的验证码信息
   - 确认token生成正确

3. **使用测试邮箱**
   - 先使用自己的邮箱测试
   - 确认能收到验证码后再使用其他邮箱

## 技术支持

如遇到问题，请提供以下信息：
1. 使用的邮箱服务商
2. 具体的错误信息
3. 后端日志输出
4. 前端控制台错误
