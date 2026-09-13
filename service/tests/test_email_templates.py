"""邮件模板的静态检查 —— 不碰 SMTP，只验证渲染出来的 HTML。

主要防两类回归：
  1. 配色又漂回旧的红色主题（跟站内登录/注册页不一致）
  2. 用上 Outlook 不支持的 CSS（渐变按钮会变成白底白字，直接隐形）
"""

import pytest

from app.services.email_service import (
    DEFAULT_LOGO_URL,
    PRIMARY,
    password_reset_email_html,
    verification_email_html,
)


def test_verification_email_matches_site_theme():
    html = verification_email_html("123456", 10)

    assert "123456" in html
    assert "10 分钟" in html
    assert DEFAULT_LOGO_URL in html
    assert PRIMARY in html


def test_password_reset_email_matches_site_theme():
    link = "https://nlnoj.gr3yph4ntom.cn/reset-password?token=abc123"
    html = password_reset_email_html(link, 30)

    assert link in html
    assert "30 分钟" in html
    assert DEFAULT_LOGO_URL in html
    assert PRIMARY in html


@pytest.mark.parametrize(
    "render",
    [
        lambda: verification_email_html("123456", 10),
        lambda: password_reset_email_html("https://example.com/x", 30),
    ],
    ids=["verification", "password-reset"],
)
def test_email_avoids_stale_theme_and_unsupported_css(render):
    html = render()

    # 旧的红色主题（现在是站点的「危险色」，不该出现在邮件里）
    assert "#e74c3c" not in html
    assert "#c0392b" not in html
    assert "#3b82f6" not in html
    # Outlook（Word 渲染引擎）不支持 CSS 渐变：一旦只有渐变色，
    # 背景会变成透明，白字直接看不见。所以只能用纯色。
    assert "linear-gradient" not in html


def test_logo_url_can_be_overridden():
    html = verification_email_html("000000", 10, logo_url="https://example.com/a.png")

    assert "https://example.com/a.png" in html
    assert DEFAULT_LOGO_URL not in html


def test_prod_rejects_localhost_frontend_url():
    """ENV=prod 时前端地址还留着 localhost，必须启动即报错，
    否则用户收到的密码重置链接会指向 localhost。"""
    from app.core.config import Settings

    with pytest.raises(RuntimeError, match="FRONTEND_URL"):
        Settings(
            ENV="prod",
            JWT_SECRET="x" * 32,
            DATABASE_URL="postgresql+asyncpg://u:p@host:5432/db",
            FRONTEND_URL="http://localhost:5173",
        )

    # 配对了就应该正常
    cfg = Settings(
        ENV="prod",
        JWT_SECRET="x" * 32,
        DATABASE_URL="postgresql+asyncpg://u:p@host:5432/db",
        FRONTEND_URL="https://nlnoj.gr3yph4ntom.cn",
    )
    assert cfg.FRONTEND_URL == "https://nlnoj.gr3yph4ntom.cn"
