"""Application entrypoint.

Run the development server with:

    uv run uvicorn app.main:app --reload
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from dotenv import load_dotenv

from app.api.router import api_router

# 加载环境变量
load_dotenv()

TAGS_METADATA = [
    {"name": "users", "description": "用户资源：注册新用户、获取当前登录用户。"},
    {"name": "tokens", "description": "令牌资源：用凭据签发令牌（登录）、刷新并轮换令牌。"},
]

# 自定义 Swagger UI 页面：中文标题 + 客户端界面汉化脚本。
# Swagger UI 本身没有官方 i18n，这里通过文本节点替换做汉化（尽力覆盖主要控件）。
SWAGGER_UI_HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>OJ 在线判题系统 - API 文档</title>
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css" />
  <style>
    html { box-sizing: border-box; overflow-y: auto; }
    *, *::before, *::after { box-sizing: inherit; }
    body { margin: 0; background: #fafafa; }
    body, input, textarea, select, button { font-family: "Segoe UI", "Microsoft YaHei", -apple-system, sans-serif; }
  </style>
</head>
<body>
  <div id="swagger-ui"></div>
  <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js" charset="UTF-8"></script>
  <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-standalone-preset.js" charset="UTF-8"></script>
  <script>
    window.onload = function () {
      window.ui = SwaggerUIBundle({
        url: "/openapi.json",
        dom_id: "#swagger-ui",
        deepLinking: true,
        presets: [SwaggerUIBundle.presets.apis, SwaggerUIStandalonePreset],
        plugins: [SwaggerUIBundle.plugins.DownloadUrl],
        layout: "StandaloneLayout",
        oauth2RedirectUrl: window.location.origin + "/docs/oauth2-redirect"
      });

      // ---------- 界面汉化（英文 -> 中文）----------
      var dict = {
        "Authorize": "授权", "Logout": "退出登录", "Authorizing...": "授权中...",
        "Try it out": "试一下", "Execute": "执行", "Clear": "清空",
        "Lock": "锁定", "Unlock": "解锁", "Close": "关闭", "Cancel": "取消",
        "Responses": "响应", "Response body": "响应体", "Response headers": "响应头",
        "Response": "响应", "Request body": "请求体", "Parameters": "参数",
        "Headers": "请求头", "No headers": "无请求头", "No parameters": "无参数",
        "Schema": "数据结构", "Schemas": "数据模型", "Example": "示例", "Examples": "示例",
        "Model": "模型", "Models": "数据模型", "Loading...": "加载中...",
        "Servers": "服务器", "Copy": "复制", "Expand all": "全部展开",
        "Collapse all": "全部折叠", "Hide": "隐藏", "Filters": "筛选", "Search": "搜索",
        "Available values:": "可选值：", "Default value:": "默认值：",
        "Possible values:": "可能的值：", "Enum:": "枚举：",
        "username": "用户名", "password": "密码", "name": "名称", "description": "描述",
        "type": "类型", "string": "字符串", "integer": "整数", "boolean": "布尔",
        "array": "数组", "object": "对象", "Required": "必填", "required": "必填",
        "readOnly": "只读", "writeOnly": "只写", "deprecated": "已弃用", "nullable": "可为空",
        "Title": "标题", "Version": "版本", "Contact": "联系人", "License": "许可证"
      };
      function translate(root) {
        if (!root) return;
        var walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, null, false);
        var nodes = [];
        while (walker.nextNode()) nodes.push(walker.currentNode);
        nodes.forEach(function (n) {
          var key = n.nodeValue.replace(/^\\s+|\\s+$/g, "");
          if (dict[key]) n.nodeValue = n.nodeValue.replace(key, dict[key]);
        });
        root.querySelectorAll("[title],[placeholder],[aria-label]").forEach(function (el) {
          ["title", "placeholder", "aria-label"].forEach(function (attr) {
            var v = el.getAttribute(attr);
            if (v && dict[v.trim()]) el.setAttribute(attr, dict[v.trim()]);
          });
        });
      }
      var target = document.getElementById("swagger-ui");
      translate(target);
      var mo = new MutationObserver(function () { translate(target); });
      mo.observe(target, { childList: true, subtree: true });
    };
  </script>
</body>
</html>
"""

app = FastAPI(
    title="OJ 在线判题系统",
    description="用户认证服务 API 文档。",
    version="0.1.0",
    openapi_tags=TAGS_METADATA,
    docs_url=None,  # 关闭默认 /docs，改用下面的中文版
)

# CORS：v1 用 Bearer 头鉴权（非 cookie），放宽源是安全的；若改 cookie 鉴权需收紧。
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html() -> HTMLResponse:
    """中文版 Swagger UI。"""
    return HTMLResponse(SWAGGER_UI_HTML)


@app.get("/")
def read_root() -> dict[str, str]:
    """健康检查。"""
    return {"message": "Hello, World!"}


@app.get("/hello/{name}")
def hello(name: str) -> dict[str, str]:
    """路径参数示例。"""
    return {"message": f"Hello, {name}!"}
