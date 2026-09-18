"""客户端真实 IP 提取。

部署链路：客户端 -> 宝塔 nginx(443) -> 容器 nginx(80) -> uvicorn(8000)。
宝塔以覆盖式 ``proxy_set_header X-Real-IP $remote_addr`` 注入真实客户端 IP
（客户端伪造的同名头会被覆盖），容器 nginx 透传该头（见 web/nginx.conf 的 map）。
因此 ``X-Real-IP`` 是唯一不可伪造的来源，缺失时（本地直连开发环境）回退
对端地址。
"""

from __future__ import annotations

from fastapi import Request


def get_client_ip(request: Request) -> str:
    xrip = (request.headers.get("x-real-ip") or "").strip()
    if xrip:
        return xrip
    return request.client.host if request.client else "unknown"
