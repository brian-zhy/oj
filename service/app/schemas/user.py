"""用户的 Pydantic 模型。"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    username: str = Field(
        min_length=3,
        max_length=50,
        pattern=r"^[A-Za-z0-9_]+$",
        description="用户名，3-50 位字母、数字或下划线",
    )
    email: EmailStr | None = Field(None, description="邮箱地址（邮箱注册时必填）")
    phone: str | None = Field(None, description="手机号（手机注册时必填）")
    # 72 字符上限用于规避 bcrypt 72 字节的静默截断（ASCII 场景）。
    password: str = Field(min_length=8, max_length=72, description="密码，8-72 位")
    email_token: str | None = Field(None, description="邮箱验证令牌（邮箱注册时必填）")
    email_code: str | None = Field(None, description="邮箱验证码（邮箱注册时必填）")
    phone_token: str | None = Field(None, description="手机验证令牌（手机注册时必填）")
    phone_code: str | None = Field(None, description="手机验证码（手机注册时必填）")


class UserLogin(BaseModel):
    identifier: str = Field(description="用户名、UID、手机或电子邮箱")
    password: str = Field(description="密码")
    captcha: str = Field(description="图形验证码")
    captcha_id: str = Field(description="验证码ID")


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description="用户 ID")
    username: str = Field(description="用户名")
    email: EmailStr = Field(description="邮箱")
    user_number: int = Field(description="用户编号")
    phone: str | None = Field(None, description="手机号")
    is_active: bool = Field(description="是否启用")
    is_banned: bool = Field(description="是否被封禁")
    is_admin: bool = Field(description="是否管理员")
    is_super_admin: bool = Field(description="是否超级管理员")
    is_cheater: bool = Field(description="是否作弊者")
    can_speak: bool = Field(description="发言权限")
    can_manage_users: bool = Field(description="用户管理权限")
    can_manage_posts: bool = Field(description="帖子管理权限")
    can_assign_admin: bool = Field(description="授予管理员权限")
    avatar_url: str | None = Field(None, description="头像URL")
    user_tag: str | None = Field(None, description="用户标签")
    username_color: str | None = Field(None, description="用户名颜色")
    bio: str | None = Field(None, description="个人简介")
    created_at: datetime = Field(description="创建时间")


class UserProfileUpdate(BaseModel):
    username: str | None = Field(None, min_length=3, max_length=50, description="用户名")
    bio: str | None = Field(None, description="个人简介")
    avatar_url: str | None = Field(None, description="头像URL")
    user_tag: str | None = Field(None, max_length=100, description="用户标签")
    username_color: str | None = Field(None, max_length=20, description="用户名颜色")


class PasswordUpdate(BaseModel):
    old_password: str = Field(description="旧密码")
    new_password: str = Field(min_length=8, max_length=72, description="新密码")


class UserAdminUpdate(BaseModel):
    """管理员用户更新模式"""
    username: str | None = Field(None, min_length=3, max_length=50, description="用户名")
    email: EmailStr | None = Field(None, description="邮箱")
    bio: str | None = Field(None, max_length=500, description="个人简介")
    avatar_url: str | None = Field(None, max_length=500, description="头像URL")
    user_tag: str | None = Field(None, max_length=100, description="用户标签")
    username_color: str | None = Field(None, max_length=20, description="用户名颜色")
    remark: str | None = Field(None, max_length=100, description="管理员备注名")

    # 管理员权限字段（仅管理员可修改）
    is_admin: bool | None = Field(None, description="管理员权限")
    is_super_admin: bool | None = Field(None, description="超级管理员权限")
    can_manage_users: bool | None = Field(None, description="用户管理权限")
    can_manage_posts: bool | None = Field(None, description="帖子管理权限")
    can_assign_admin: bool | None = Field(None, description="授予管理员权限")
    can_speak: bool | None = Field(None, description="发言权限")
    is_banned: bool | None = Field(None, description="封禁状态")
    is_cheater: bool | None = Field(None, description="作弊者标记")


class UserAdminResponse(BaseModel):
    """管理员用户响应模式"""
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description="用户 ID")
    username: str = Field(description="用户名")
    email: EmailStr = Field(description="邮箱")
    user_number: int = Field(description="用户编号")
    phone: str | None = Field(None, description="手机号")
    is_active: bool = Field(description="是否启用")
    is_banned: bool = Field(description="是否被封禁")
    is_cheater: bool = Field(description="是否作弊者")
    is_super_admin: bool = Field(description="是否超级管理员")
    is_admin: bool = Field(description="是否管理员")
    can_speak: bool = Field(description="发言权限")
    can_manage_users: bool = Field(description="用户管理权限")
    can_manage_posts: bool = Field(description="帖子管理权限")
    can_assign_admin: bool = Field(description="授予管理员权限")
    avatar_url: str | None = Field(None, description="头像URL")
    user_tag: str | None = Field(None, description="用户标签")
    username_color: str | None = Field(None, description="用户名颜色")
    bio: str | None = Field(None, description="个人简介")
    remark: str | None = Field(None, description="管理员备注名")
    last_seen: datetime | None = Field(None, description="最后在线时间")
    created_at: datetime = Field(description="创建时间")
    updated_at: datetime = Field(description="更新时间")
