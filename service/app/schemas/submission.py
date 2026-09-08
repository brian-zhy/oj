"""提交的 Pydantic 模型。"""

from __future__ import annotations

from pydantic import BaseModel, Field

# 支持的语言（评测沙箱依赖宿主机安装 g++ / gcc / python3）
LANGUAGES = ["cpp", "c", "python3"]
_LANG = "|".join(LANGUAGES)


class SubmissionCreate(BaseModel):
    code: str = Field(min_length=1, max_length=100_000, description="源代码")
    language: str = Field(pattern=f"^({_LANG})$", description="语言：cpp / c / python3")


class TestCaseCreate(BaseModel):
    input_data: str = Field(default="", max_length=1_000_000, description="测试点输入")
    expected_output: str = Field(default="", max_length=1_000_000, description="期望输出")
