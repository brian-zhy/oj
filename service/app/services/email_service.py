"""邮件发送服务。"""

from __future__ import annotations

import logging
import os
import smtplib
from email.message import EmailMessage
from email.utils import formataddr
from typing import Any

# 配置日志
logger = logging.getLogger(__name__)


class EmailService:
    """邮件发送服务类。"""

    def __init__(self):
        """初始化邮件服务。"""
        self.enabled = True
        # 延迟加载配置，在需要时从环境变量获取
        self._smtp_host = None
        self._smtp_port = None
        self._smtp_email = None
        self._smtp_password = None
        self._from_name = None
        self._is_configured = None
        self._config_loaded = False  # 添加配置加载状态标记

    def _load_config(self):
        """从环境变量加载SMTP配置。"""
        if self._config_loaded:  # 如果已经加载过，直接返回
            return

        # 强制重新加载环境变量（解决启动时环境变量未加载的问题）
        from dotenv import load_dotenv
        load_dotenv()

        self._smtp_host = os.getenv("SMTP_HOST", "smtp.qq.com")
        self._smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self._smtp_email = os.getenv("SMTP_EMAIL", "")
        self._smtp_password = os.getenv("SMTP_PASSWORD", "")
        self._from_name = os.getenv("SMTP_FROM_NAME", "Jason227")
        self._is_configured = bool(self._smtp_email and self._smtp_password)
        self._config_loaded = True  # 标记配置已加载

        if not self._is_configured:
            logger.warning("邮件服务未配置，将使用演示模式")
        else:
            logger.info(f"邮件服务已配置: {self._smtp_email}")

    @property
    def smtp_host(self):
        self._load_config()
        return self._smtp_host

    @property
    def smtp_port(self):
        self._load_config()
        return self._smtp_port

    @property
    def smtp_email(self):
        self._load_config()
        return self._smtp_email

    @property
    def smtp_password(self):
        self._load_config()
        return self._smtp_password

    @property
    def from_name(self):
        self._load_config()
        return self._from_name

    @property
    def is_configured(self):
        self._load_config()
        return self._is_configured

    async def send_verification_email(
        self,
        email: str,
        code: str,
        expiry_minutes: int = 10
    ) -> bool:
        """发送验证码邮件。

        Args:
            email: 收件人邮箱
            code: 验证码
            expiry_minutes: 过期时间（分钟）

        Returns:
            发送是否成功
        """
        try:
            # 如果配置了SMTP，发送真实邮件
            if self.is_configured:
                logger.info(f"使用真实SMTP模式发送邮件至 {email}")
                return await self._send_real_email(email, code, expiry_minutes)
            else:
                # 演示模式：在控制台输出验证码信息
                logger.info(f"[Email] Send to: {email}")
                logger.info(f"[Email] Code: {code}")
                logger.info(f"[Email] Expiry: {expiry_minutes} minutes")
                print(f"[Demo] 邮箱验证码发送至 {email}: {code}")
                return True

        except Exception as e:
            logger.error(f"发送邮件失败: {e}")
            return False

    async def _send_real_email(
        self,
        email: str,
        code: str,
        expiry_minutes: int
    ) -> bool:
        """发送真实邮件。

        Args:
            email: 收件人邮箱
            code: 验证码
            expiry_minutes: 过期时间（分钟）

        Returns:
            发送是否成功
        """
        try:
            # 创建邮件消息
            message = EmailMessage()
            message["From"] = formataddr((self.from_name, self.smtp_email))
            message["To"] = email
            message["Subject"] = "【Jason227】邮箱验证码"

            # HTML邮件内容
            html_content = f"""
            <html>
            <body style="font-family: 'Segoe UI', Arial, sans-serif; background-color: #f5f7fa; margin: 0; padding: 20px;">
                <div style="max-width: 600px; margin: 0 auto; background: white; border-radius: 12px; padding: 32px; box-shadow: 0 2px 8px rgba(0,0,0,0.04);">
                    <h2 style="color: #e74c3c; margin: 0 0 20px 0; font-size: 24px;">✨ Jason227 邮箱验证</h2>

                    <p style="color: #5b6e8c; font-size: 16px; line-height: 1.6;">您好！</p>

                    <p style="color: #5b6e8c; font-size: 16px; line-height: 1.6;">
                        您正在注册 Jason227 账户，验证码如下：
                    </p>

                    <div style="background: linear-gradient(135deg, #e74c3c 0%, #c0392b 100%); padding: 24px; text-align: center; font-size: 32px; font-weight: bold; margin: 24px 0; border-radius: 8px; color: white; letter-spacing: 4px;">
                        {code}
                    </div>

                    <p style="color: #5b6e8c; font-size: 16px; line-height: 1.6;">
                        验证码有效期为 <strong style="color: #e74c3c;">{expiry_minutes} 分钟</strong>，请及时使用。
                    </p>

                    <p style="color: #999; font-size: 14px; line-height: 1.6; margin: 24px 0 8px 0;">
                        如果这不是您本人操作，请忽略此邮件。
                    </p>

                    <hr style="border: none; border-top: 1px solid #eee; margin: 24px 0;">

                    <p style="color: #999; font-size: 12px; text-align: center; margin: 0;">
                        此邮件由系统自动发送，请勿回复。
                    </p>
                </div>
            </body>
            </html>
            """

            message.set_content(html_content, subtype='html')

            # 连接SMTP服务器并发送邮件，增加重试机制
            max_retries = 2
            for attempt in range(max_retries):
                try:
                    # 465端口使用SSL，587端口使用TLS
                    if self.smtp_port == 465:
                        logger.info(f"尝试 {attempt + 1}/{max_retries}: 使用SSL连接到 {self.smtp_host}:{self.smtp_port}")
                        with smtplib.SMTP_SSL(self.smtp_host, self.smtp_port, timeout=15) as server:
                            server.login(self.smtp_email, self.smtp_password)
                            logger.info(f"SMTP登录成功: {self.smtp_email}")
                            server.send_message(message)
                            logger.info(f"邮件已发送至 {email}")
                    else:
                        logger.info(f"尝试 {attempt + 1}/{max_retries}: 使用TLS连接到 {self.smtp_host}:{self.smtp_port}")
                        with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=15) as server:
                            server.ehlo()
                            server.starttls()
                            server.ehlo()
                            server.login(self.smtp_email, self.smtp_password)
                            logger.info(f"SMTP登录成功: {self.smtp_email}")
                            server.send_message(message)
                            logger.info(f"邮件已发送至 {email}")

                    return True

                except smtplib.SMTPAuthenticationError as e:
                    error_msg = f"SMTP认证失败: {str(e)}"
                    logger.error(error_msg)
                    logger.error(f"SMTP配置: host={self.smtp_host}, port={self.smtp_port}, email={self.smtp_email}")
                    # 认证失败不需要重试
                    raise Exception(f"邮箱配置错误，请检查SMTP账号密码")

                except smtplib.SMTPException as e:
                    if attempt < max_retries - 1:
                        logger.warning(f"SMTP发送失败，重试中... (尝试 {attempt + 1}/{max_retries}): {str(e)}")
                        continue
                    else:
                        error_msg = f"SMTP发送邮件失败: {str(e)}"
                        logger.error(error_msg)
                        logger.error(f"SMTP配置: host={self.smtp_host}, port={self.smtp_port}, email={self.smtp_email}")
                        raise Exception(f"邮件发送失败: {str(e)}")

                except Exception as e:
                    error_msg = f"发送邮件时发生意外错误: {str(e)}"
                    logger.error(error_msg)
                    logger.error(f"SMTP配置: host={self.smtp_host}, port={self.smtp_port}, email={self.smtp_email}")
                    raise Exception(f"邮件发送失败: {str(e)}")

        except Exception as e:
            # 捕获所有异常并重新抛出
            if isinstance(e, Exception):
                raise e
            else:
                raise Exception(f"邮件发送失败: {str(e)}")

    async def send_password_reset_email(
        self,
        email: str,
        reset_link: str,
        expiry_minutes: int = 30
    ) -> bool:
        """发送密码重置邮件。

        Args:
            email: 收件人邮箱
            reset_link: 密码重置链接
            expiry_minutes: 过期时间（分钟）

        Returns:
            发送是否成功
        """
        try:
            # 如果配置了SMTP，发送真实邮件
            if self.is_configured:
                logger.info(f"使用真实SMTP模式发送密码重置邮件至 {email}")
                print(f"[SMTP] 准备发送密码重置邮件至 {email}")
                return await self._send_password_reset_real_email(email, reset_link, expiry_minutes)
            else:
                # 演示模式：在控制台输出重置链接
                logger.info(f"[Email] Send to: {email}")
                logger.info(f"[Email] Reset Link: {reset_link}")
                logger.info(f"[Email] Expiry: {expiry_minutes} minutes")
                print(f"[Demo] 密码重置邮件发送至 {email}")
                print(f"[Demo] 重置链接: {reset_link}")
                print(f"[Demo] 有效期: {expiry_minutes} 分钟")
                return True

        except Exception as e:
            logger.error(f"发送密码重置邮件失败: {e}")
            return False

    async def _send_password_reset_real_email(
        self,
        email: str,
        reset_link: str,
        expiry_minutes: int
    ) -> bool:
        """发送真实的密码重置邮件。

        Args:
            email: 收件人邮箱
            reset_link: 密码重置链接
            expiry_minutes: 过期时间（分钟）

        Returns:
            发送是否成功
        """
        try:
            # 创建邮件消息
            message = EmailMessage()
            message["From"] = formataddr((self.from_name, self.smtp_email))
            message["To"] = email
            message["Subject"] = "【Jason227】密码重置请求"

            # HTML邮件内容
            html_content = f"""
            <html>
            <body style="font-family: 'Segoe UI', Arial, sans-serif; background-color: #f5f7fa; margin: 0; padding: 20px;">
                <div style="max-width: 600px; margin: 0 auto; background: white; border-radius: 12px; padding: 32px; box-shadow: 0 2px 8px rgba(0,0,0,0.04);">
                    <h2 style="color: #e74c3c; margin: 0 0 20px 0; font-size: 24px;">✨ Jason227 密码重置</h2>

                    <p style="color: #5b6e8c; font-size: 16px; line-height: 1.6;">您好！</p>

                    <p style="color: #5b6e8c; font-size: 16px; line-height: 1.6;">
                        我们收到了您的密码重置请求。点击下面的按钮重置您的密码：
                    </p>

                    <div style="text-align: center; margin: 32px 0;">
                        <a href="{reset_link}" style="display: inline-block; background: linear-gradient(135deg, #e74c3c 0%, #c0392b 100%); color: white; padding: 16px 32px; text-decoration: none; border-radius: 40px; font-size: 16px; font-weight: 600;">
                            重置密码
                        </a>
                    </div>

                    <p style="color: #5b6e8c; font-size: 14px; line-height: 1.6;">
                        或者复制以下链接到浏览器中打开：
                    </p>

                    <p style="color: #3b82f6; font-size: 13px; word-break: break-all; background: #f9fafb; padding: 12px; border-radius: 8px; margin: 16px 0;">
                        {reset_link}
                    </p>

                    <p style="color: #5b6e8c; font-size: 16px; line-height: 1.6;">
                        此链接有效期为 <strong style="color: #e74c3c;">{expiry_minutes} 分钟</strong>。
                    </p>

                    <p style="color: #999; font-size: 14px; line-height: 1.6; margin: 24px 0 8px 0;">
                        如果这不是您本人操作，请忽略此邮件，您的密码不会被更改。
                    </p>

                    <hr style="border: none; border-top: 1px solid #eee; margin: 24px 0;">

                    <p style="color: #999; font-size: 12px; text-align: center; margin: 0;">
                        此邮件由系统自动发送，请勿回复。
                    </p>
                </div>
            </body>
            </html>
            """

            message.set_content(html_content, subtype='html')

            # 连接SMTP服务器并发送邮件，增加重试机制
            max_retries = 2
            for attempt in range(max_retries):
                try:
                    # 465端口使用SSL，587端口使用TLS
                    if self.smtp_port == 465:
                        logger.info(f"尝试 {attempt + 1}/{max_retries}: 使用SSL连接到 {self.smtp_host}:{self.smtp_port}")
                        with smtplib.SMTP_SSL(self.smtp_host, self.smtp_port, timeout=15) as server:
                            server.login(self.smtp_email, self.smtp_password)
                            logger.info(f"SMTP登录成功: {self.smtp_email}")
                            server.send_message(message)
                            logger.info(f"密码重置邮件已发送至 {email}")
                    else:
                        logger.info(f"尝试 {attempt + 1}/{max_retries}: 使用TLS连接到 {self.smtp_host}:{self.smtp_port}")
                        with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=15) as server:
                            server.ehlo()
                            server.starttls()
                            server.ehlo()
                            server.login(self.smtp_email, self.smtp_password)
                            logger.info(f"SMTP登录成功: {self.smtp_email}")
                            server.send_message(message)
                            logger.info(f"密码重置邮件已发送至 {email}")

                    return True

                except smtplib.SMTPAuthenticationError as e:
                    error_msg = f"SMTP认证失败: {str(e)}"
                    logger.error(error_msg)
                    logger.error(f"SMTP配置: host={self.smtp_host}, port={self.smtp_port}, email={self.smtp_email}")
                    # 认证失败不需要重试
                    raise Exception(f"邮箱配置错误，请检查SMTP账号密码")

                except smtplib.SMTPException as e:
                    if attempt < max_retries - 1:
                        logger.warning(f"SMTP发送失败，重试中... (尝试 {attempt + 1}/{max_retries}): {str(e)}")
                        continue
                    else:
                        error_msg = f"SMTP发送密码重置邮件失败: {str(e)}"
                        logger.error(error_msg)
                        logger.error(f"SMTP配置: host={self.smtp_host}, port={self.smtp_port}, email={self.smtp_email}")
                        raise Exception(f"密码重置邮件发送失败: {str(e)}")

                except Exception as e:
                    error_msg = f"发送密码重置邮件时发生意外错误: {str(e)}"
                    logger.error(error_msg)
                    logger.error(f"SMTP配置: host={self.smtp_host}, port={self.smtp_port}, email={self.smtp_email}")
                    raise Exception(f"密码重置邮件发送失败: {str(e)}")

        except Exception as e:
            # 捕获所有异常并重新抛出
            if isinstance(e, Exception):
                raise e
            else:
                raise Exception(f"密码重置邮件发送失败: {str(e)}")


# 创建邮件服务实例
email_service = EmailService()
