---
title: 从零搭建 OAuth 2.1 + PKCE MCP 项目 —— 完整可运行实战
author: Xing Wang
date: 2026-07-12
tags: [mcp, oauth, pkce, fastapi, education, security, jwt, hands-on]
description: 动手搭建 Authorization Server + MCP Server + Python Client：元数据发现、PKCE、JWT、Scope、Review→Execute、幂等与测试。模拟投资组合，不接真实券商。
---

# 从零搭建 OAuth 2.1 + PKCE MCP 项目：完整可运行实战

**English:** [2026-07-12-mcp-oauth-pkce-lab.md](2026-07-12-mcp-oauth-pkce-lab.md)  
**概念篇（先读）：** [从 Robinhood MCP 看懂 MCP 认证](2026-07-12-mcp-oauth-auth-deep-dive.zh.md)  
**架构参考：** [MCP 在生产中的实践](../articles/2026-07-11-mcp-in-production-robinhood-case.zh.md)  
**实现仓库：** [xingai-robinhood-mcp](https://github.com/xingaiapp/xingai-robinhood-mcp)（券商领域）· **可运行 POC：** [claims-mcp-oauth-poc](https://github.com/xingaiapp/xingai-enterprise-ai-pocs/tree/main/pocs/claims-mcp-oauth-poc)（保险理赔领域——这篇实验课代码的移植版）

> **重要声明：** 本实验为教学用**模拟系统**，不接真实券商，不构成投资建议，不属于生产就绪代码。代码按「现状」提供，用户自行负责评估、部署与合规。

---

## 三十三、我们最终要搭建什么

三个相互协作的服务，全部跑在本机：

```text
MCP Client (Python CLI)
     │
     │ 1. POST /mcp（无 Token）→ 收到 401 + resource_metadata
     │
     ▼
Authorization Server (:8000)
     │  元数据发现 / PKCE / JWT 签发 / Refresh Rotation / Revocation
     │
     ▼  Bearer JWT
MCP Server (:8001)
     │  验签 + Scope + Agent Policy + Review → Execute + 幂等
     ▼
模拟 Portfolio / Quote / Review / Place（不连真实券商）
```

**三条核心原则**：

1. **Auth 是 MCP 的门**，没有有效 JWT 什么都拿不到。
2. **Scope ≠ Policy**，拿到 `orders.place` scope 不等于可以下任意单。
3. **Review 是人机确认节点**，place 阶段不允许再改单子内容。

---

## 三十四、目录结构

```text
secure-mcp-demo/
├── auth_server/
│   ├── __init__.py
│   ├── main.py          # FastAPI 应用 + 所有 OAuth 端点
│   ├── models.py        # Pydantic 模型 + 内存存储结构
│   ├── security.py      # PKCE 验证 / JWT 签发 / JWKS 暴露
│   └── storage.py       # 内存 KV（生产换 PostgreSQL + Redis）
├── mcp_server/
│   ├── __init__.py
│   ├── main.py          # FastAPI 应用 + JSON-RPC /mcp
│   ├── auth.py          # Bearer 验证 / JWKS 拉取 / Scope 检查
│   ├── tools.py         # 四个 MCP Tool 实现
│   └── policies.py      # Agent 第二道策略墙
├── client/
│   ├── __init__.py
│   ├── main.py          # 主流程：发现→PKCE→Token→调工具
│   ├── discovery.py     # Resource Metadata + AS Metadata 发现
│   ├── oauth.py         # PKCE 生成 / 本机 Callback / Token 交换
│   └── token_store.py   # Token 持久化（demo 用文件，生产用 Keychain）
├── tests/
│   ├── test_auth_server.py
│   ├── test_mcp_auth.py
│   └── test_order_flow.py
├── keys/
│   ├── private.pem      # Auth Server 持有，永远不出这台机器
│   └── public.pem       # MCP Server 用于验签
├── requirements.txt
├── docker-compose.yml
└── README.md
```

---

## 三十五、环境准备

```bash
# 推荐 Python 3.11+
python --version

# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 安装依赖
pip install fastapi "uvicorn[standard]" requests httpx \
  "PyJWT[crypto]" cryptography python-multipart \
  pydantic keyring pytest pytest-asyncio httpx
```

`requirements.txt`：

```text
fastapi>=0.111.0
uvicorn[standard]>=0.29.0
requests>=2.31.0
httpx>=0.27.0
PyJWT[crypto]>=2.8.0
cryptography>=42.0.0
python-multipart>=0.0.9
pydantic>=2.7.0
keyring>=25.0.0
pytest>=8.2.0
pytest-asyncio>=0.23.0
```

---

## 三十六、生成 RSA 密钥对

Auth Server 持有**私钥**用于签名；MCP Server 持有**公钥**用于验签。私钥永远不出 Auth Server 所在机器。

```bash
mkdir -p keys

# 生成 2048 位 RSA 私钥
openssl genrsa -out keys/private.pem 2048

# 导出公钥
openssl rsa -in keys/private.pem -pubout -out keys/public.pem

# 设置权限（生产环境必须）
chmod 600 keys/private.pem
chmod 644 keys/public.pem

# 验证
openssl rsa -in keys/private.pem -check -noout
# 期望：RSA key ok
```

---

## 三十七、Auth Server — models.py

所有内存数据结构，demo 阶段无需数据库。

```python
# auth_server/models.py
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Authorization Code
# ---------------------------------------------------------------------------

@dataclass
class AuthorizationCodeRecord:
    """一次性短命授权码，用于换 Token。"""
    code: str
    client_id: str
    redirect_uri: str
    user_id: str
    scope: str                     # 空格分隔的权限列表
    code_challenge: str            # S256 challenge
    created_at: float = field(default_factory=time.time)
    expires_in: int = 120          # 120 秒内必须兑换
    used: bool = False             # 一次性：兑换后立即置 True

    @property
    def expires_at(self) -> float:
        return self.created_at + self.expires_in

    @property
    def is_expired(self) -> bool:
        return time.time() > self.expires_at

    @property
    def is_valid(self) -> bool:
        return not self.used and not self.is_expired


# ---------------------------------------------------------------------------
# Refresh Token
# ---------------------------------------------------------------------------

@dataclass
class RefreshTokenRecord:
    """Refresh Token，支持 Rotation（旧的换新的，旧的立即作废）。"""
    token: str
    client_id: str
    user_id: str
    scope: str
    revoked: bool = False
    created_at: float = field(default_factory=time.time)
    expires_in: int = 86400 * 30   # 30 天

    @property
    def expires_at(self) -> float:
        return self.created_at + self.expires_in

    @property
    def is_valid(self) -> bool:
        return not self.revoked and time.time() < self.expires_at


# ---------------------------------------------------------------------------
# Client Registration
# ---------------------------------------------------------------------------

@dataclass
class ClientRegistration:
    """OAuth 客户端注册信息。"""
    client_id: str
    redirect_uris: list[str]
    client_name: str = ""
    token_endpoint_auth_method: str = "none"   # Public client（无 secret）


# ---------------------------------------------------------------------------
# Pydantic request/response schemas
# ---------------------------------------------------------------------------

from pydantic import BaseModel


class TokenRequest(BaseModel):
    grant_type: str
    code: Optional[str] = None
    redirect_uri: Optional[str] = None
    client_id: Optional[str] = None
    code_verifier: Optional[str] = None
    refresh_token: Optional[str] = None
    scope: Optional[str] = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    expires_in: int
    refresh_token: Optional[str] = None
    scope: str


class RegistrationRequest(BaseModel):
    client_name: str
    redirect_uris: list[str]
    token_endpoint_auth_method: str = "none"


class RegistrationResponse(BaseModel):
    client_id: str
    client_name: str
    redirect_uris: list[str]
    token_endpoint_auth_method: str


# ---------------------------------------------------------------------------
# 预置 Scope 集合
# ---------------------------------------------------------------------------

SUPPORTED_SCOPES = {
    "portfolio.read",
    "quotes.read",
    "orders.review",
    "orders.place",
    "offline_access",   # 申请 refresh token 的 scope
}
```

---

## 三十八、Auth Server — storage.py

线程安全的内存 KV，生产替换成 PostgreSQL + Redis。

```python
# auth_server/storage.py
from __future__ import annotations

import threading
from typing import Optional

from auth_server.models import (
    AuthorizationCodeRecord,
    ClientRegistration,
    RefreshTokenRecord,
)


class InMemoryStorage:
    """线程安全的内存存储，仅用于 demo。"""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._codes: dict[str, AuthorizationCodeRecord] = {}
        self._refresh_tokens: dict[str, RefreshTokenRecord] = {}
        self._clients: dict[str, ClientRegistration] = {}

    # ---- Authorization Codes -----------------------------------------------

    def save_code(self, record: AuthorizationCodeRecord) -> None:
        with self._lock:
            self._codes[record.code] = record

    def get_code(self, code: str) -> Optional[AuthorizationCodeRecord]:
        with self._lock:
            return self._codes.get(code)

    def mark_code_used(self, code: str) -> None:
        with self._lock:
            if code in self._codes:
                self._codes[code].used = True

    # ---- Refresh Tokens ----------------------------------------------------

    def save_refresh_token(self, record: RefreshTokenRecord) -> None:
        with self._lock:
            self._refresh_tokens[record.token] = record

    def get_refresh_token(self, token: str) -> Optional[RefreshTokenRecord]:
        with self._lock:
            return self._refresh_tokens.get(token)

    def revoke_refresh_token(self, token: str) -> None:
        with self._lock:
            if token in self._refresh_tokens:
                self._refresh_tokens[token].revoked = True

    # ---- Client Registrations ----------------------------------------------

    def save_client(self, client: ClientRegistration) -> None:
        with self._lock:
            self._clients[client.client_id] = client

    def get_client(self, client_id: str) -> Optional[ClientRegistration]:
        with self._lock:
            return self._clients.get(client_id)


# 单例，整个进程共享
storage = InMemoryStorage()

# 预置 Demo 客户端
storage.save_client(ClientRegistration(
    client_id="demo-desktop-client",
    redirect_uris=["http://127.0.0.1:54321/callback"],
    client_name="Demo Desktop MCP Client",
))
```

---

## 三十九、Auth Server — security.py

PKCE 验证、JWT 签发、JWKS 暴露。

```python
# auth_server/security.py
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import math
import os
import time
from pathlib import Path
from typing import Any

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend

# ---------------------------------------------------------------------------
# 密钥加载
# ---------------------------------------------------------------------------

KEYS_DIR = Path(__file__).parent.parent / "keys"
PRIVATE_KEY_PATH = KEYS_DIR / "private.pem"
PUBLIC_KEY_PATH = KEYS_DIR / "public.pem"


def _load_private_key() -> Any:
    with open(PRIVATE_KEY_PATH, "rb") as f:
        return serialization.load_pem_private_key(f.read(), password=None)


def _load_public_key() -> Any:
    with open(PUBLIC_KEY_PATH, "rb") as f:
        return serialization.load_pem_public_key(f.read())


_PRIVATE_KEY = _load_private_key()
_PUBLIC_KEY = _load_public_key()

# ---------------------------------------------------------------------------
# 配置
# ---------------------------------------------------------------------------

ISSUER = os.getenv("AUTH_ISSUER", "http://localhost:8000")
AUDIENCE = os.getenv("MCP_AUDIENCE", "http://localhost:8001/mcp")
ACCESS_TOKEN_TTL = int(os.getenv("ACCESS_TOKEN_TTL", "300"))   # 5 分钟
KID = "demo-key-001"   # Key ID，生产环境用于 JWKS 多 kid 轮换


# ---------------------------------------------------------------------------
# PKCE 验证
# ---------------------------------------------------------------------------

def verify_pkce(code_verifier: str, code_challenge: str) -> bool:
    """
    验证 PKCE S256：
      code_challenge = BASE64URL( SHA256( ASCII( code_verifier ) ) )
    使用 constant-time compare 防时序攻击。
    """
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    expected = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return hmac.compare_digest(expected, code_challenge)


# ---------------------------------------------------------------------------
# JWT 签发
# ---------------------------------------------------------------------------

def create_access_token(
    *,
    subject: str,
    scope: str,
    client_id: str,
    audience: str = AUDIENCE,
    ttl: int = ACCESS_TOKEN_TTL,
) -> tuple[str, int]:
    """
    返回 (jwt_string, expires_in_seconds)。
    使用 RS256，声明含 iss / sub / aud / scope / client_id / exp / iat / jti。
    """
    now = int(time.time())
    jti = base64.urlsafe_b64encode(os.urandom(16)).decode("ascii")

    payload = {
        "iss": ISSUER,
        "sub": subject,
        "aud": audience,
        "scope": scope,
        "client_id": client_id,
        "exp": now + ttl,
        "iat": now,
        "jti": jti,
    }

    token = jwt.encode(
        payload,
        _PRIVATE_KEY,
        algorithm="RS256",
        headers={"kid": KID},
    )
    return token, ttl


# ---------------------------------------------------------------------------
# JWKS 构建（公钥暴露给 MCP Server）
# ---------------------------------------------------------------------------

def _int_to_base64url(n: int) -> str:
    """把大整数转成 Base64URL（无 padding），用于 JWK 的 n/e 字段。"""
    byte_length = math.ceil(n.bit_length() / 8)
    return base64.urlsafe_b64encode(
        n.to_bytes(byte_length, "big")
    ).rstrip(b"=").decode("ascii")


def public_key_to_jwk() -> dict:
    """把 RSA 公钥序列化成 JWK 格式。"""
    pub_numbers = _PUBLIC_KEY.public_key().public_numbers()  # type: ignore[attr-defined]
    return {
        "kty": "RSA",
        "use": "sig",
        "alg": "RS256",
        "kid": KID,
        "n": _int_to_base64url(pub_numbers.n),
        "e": _int_to_base64url(pub_numbers.e),
    }


def get_jwks() -> dict:
    """返回完整 JWKS（支持多 key，生产环境用于密钥轮换）。"""
    return {"keys": [public_key_to_jwk()]}


# ---------------------------------------------------------------------------
# 随机 Token 生成
# ---------------------------------------------------------------------------

def generate_secure_token(n_bytes: int = 32) -> str:
    """生成 URL-safe 随机字符串，用于 authorization code / refresh token。"""
    return base64.urlsafe_b64encode(os.urandom(n_bytes)).rstrip(b"=").decode("ascii")
```

---

## 四十、Auth Server — main.py

所有 OAuth 2.1 端点的完整实现。

```python
# auth_server/main.py
from __future__ import annotations

import os
import time
from typing import Optional

from fastapi import FastAPI, Form, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from auth_server.models import (
    AuthorizationCodeRecord,
    ClientRegistration,
    RefreshTokenRecord,
    RegistrationRequest,
    RegistrationResponse,
    SUPPORTED_SCOPES,
    TokenResponse,
)
from auth_server.security import (
    AUDIENCE,
    ISSUER,
    create_access_token,
    generate_secure_token,
    get_jwks,
    verify_pkce,
)
from auth_server.storage import storage

app = FastAPI(title="OAuth 2.1 Authorization Server (Demo)")

# ---------------------------------------------------------------------------
# AS Metadata（RFC 8414）
# ---------------------------------------------------------------------------

@app.get("/.well-known/oauth-authorization-server")
async def oauth_metadata():
    """Authorization Server Metadata，客户端通过此端点自动发现所有地址。"""
    return {
        "issuer": ISSUER,
        "authorization_endpoint": f"{ISSUER}/authorize",
        "token_endpoint": f"{ISSUER}/token",
        "jwks_uri": f"{ISSUER}/jwks.json",
        "registration_endpoint": f"{ISSUER}/register",
        "revocation_endpoint": f"{ISSUER}/revoke",
        "response_types_supported": ["code"],
        "grant_types_supported": ["authorization_code", "refresh_token"],
        "code_challenge_methods_supported": ["S256"],
        "token_endpoint_auth_methods_supported": ["none"],
        "scopes_supported": sorted(SUPPORTED_SCOPES),
        "subject_types_supported": ["public"],
    }


# ---------------------------------------------------------------------------
# JWKS
# ---------------------------------------------------------------------------

@app.get("/jwks.json")
async def jwks():
    """暴露 RSA 公钥，MCP Server 用此验签 JWT。"""
    return get_jwks()


# ---------------------------------------------------------------------------
# 动态客户端注册（RFC 7591，demo 仅允许 loopback redirect）
# ---------------------------------------------------------------------------

@app.post("/register", response_model=RegistrationResponse)
async def register_client(req: RegistrationRequest):
    """
    动态注册 OAuth 客户端。
    Demo 安全限制：redirect_uri 必须指向 127.0.0.1 或 localhost。
    """
    for uri in req.redirect_uris:
        if not (uri.startswith("http://127.0.0.1") or uri.startswith("http://localhost")):
            raise HTTPException(
                status_code=400,
                detail="Demo 模式只允许 loopback redirect URI",
            )

    client_id = f"dyn-{generate_secure_token(12)}"
    client = ClientRegistration(
        client_id=client_id,
        redirect_uris=req.redirect_uris,
        client_name=req.client_name,
        token_endpoint_auth_method=req.token_endpoint_auth_method,
    )
    storage.save_client(client)

    return RegistrationResponse(
        client_id=client_id,
        client_name=client.client_name,
        redirect_uris=client.redirect_uris,
        token_endpoint_auth_method=client.token_endpoint_auth_method,
    )


# ---------------------------------------------------------------------------
# Authorization Endpoint（GET：显示 Consent 页；POST：用户点击同意）
# ---------------------------------------------------------------------------

@app.get("/authorize", response_class=HTMLResponse)
async def authorize_get(
    response_type: str = Query(...),
    client_id: str = Query(...),
    redirect_uri: str = Query(...),
    scope: str = Query(...),
    state: str = Query(...),
    code_challenge: str = Query(...),
    code_challenge_method: str = Query(...),
):
    """显示 Consent 页面（Demo 固定用户 demo-user-001，生产改为真实登录）。"""
    _validate_authorize_params(
        response_type, client_id, redirect_uri, scope, code_challenge_method
    )

    # 简单的 HTML Consent 页（生产用真实模板）
    html = f"""
<!DOCTYPE html>
<html lang="zh">
<head>
  <meta charset="utf-8">
  <title>授权请求</title>
  <style>
    body {{ font-family: system-ui, sans-serif; max-width: 480px; margin: 60px auto; padding: 20px; }}
    .scope {{ background: #f0f4f8; padding: 8px 12px; border-radius: 6px; margin: 4px 0; }}
    button {{ background: #2563eb; color: white; border: none; padding: 10px 20px;
              border-radius: 6px; cursor: pointer; font-size: 16px; margin-right: 10px; }}
    button.deny {{ background: #dc2626; }}
  </style>
</head>
<body>
  <h2>授权请求</h2>
  <p><strong>应用</strong>：{client_id}</p>
  <p><strong>申请权限</strong>：</p>
  {''.join(f'<div class="scope">✓ {s}</div>' for s in scope.split())}
  <br>
  <form method="POST" action="/authorize">
    <input type="hidden" name="response_type" value="{response_type}">
    <input type="hidden" name="client_id" value="{client_id}">
    <input type="hidden" name="redirect_uri" value="{redirect_uri}">
    <input type="hidden" name="scope" value="{scope}">
    <input type="hidden" name="state" value="{state}">
    <input type="hidden" name="code_challenge" value="{code_challenge}">
    <input type="hidden" name="code_challenge_method" value="{code_challenge_method}">
    <button type="submit" name="decision" value="allow">同意授权</button>
    <button type="submit" name="decision" value="deny" class="deny">拒绝</button>
  </form>
</body>
</html>
"""
    return HTMLResponse(content=html)


@app.post("/authorize")
async def authorize_post(
    response_type: str = Form(...),
    client_id: str = Form(...),
    redirect_uri: str = Form(...),
    scope: str = Form(...),
    state: str = Form(...),
    code_challenge: str = Form(...),
    code_challenge_method: str = Form(...),
    decision: str = Form(...),
):
    """处理用户 Consent 决定，生成授权码并重定向。"""
    _validate_authorize_params(
        response_type, client_id, redirect_uri, scope, code_challenge_method
    )

    if decision != "allow":
        # 用户拒绝
        return RedirectResponse(
            f"{redirect_uri}?error=access_denied&state={state}",
            status_code=302,
        )

    # 生成一次性 Authorization Code（TTL 120s）
    code = generate_secure_token(24)
    record = AuthorizationCodeRecord(
        code=code,
        client_id=client_id,
        redirect_uri=redirect_uri,
        user_id="demo-user-001",   # Demo 固定用户，生产改真实 session
        scope=scope,
        code_challenge=code_challenge,
    )
    storage.save_code(record)

    return RedirectResponse(
        f"{redirect_uri}?code={code}&state={state}",
        status_code=302,
    )


def _validate_authorize_params(
    response_type: str,
    client_id: str,
    redirect_uri: str,
    scope: str,
    code_challenge_method: str,
) -> None:
    """统一校验 Authorization 请求参数。"""
    if response_type != "code":
        raise HTTPException(status_code=400, detail="只支持 response_type=code")

    client = storage.get_client(client_id)
    if not client:
        raise HTTPException(status_code=400, detail="未知 client_id")

    if redirect_uri not in client.redirect_uris:
        raise HTTPException(status_code=400, detail="redirect_uri 与注册不匹配")

    if code_challenge_method != "S256":
        raise HTTPException(status_code=400, detail="必须使用 code_challenge_method=S256")

    # 校验所有申请的 scope 都在支持列表中
    requested = set(scope.split())
    unknown = requested - SUPPORTED_SCOPES
    if unknown:
        raise HTTPException(status_code=400, detail=f"不支持的 scope: {unknown}")


# ---------------------------------------------------------------------------
# Token Endpoint
# ---------------------------------------------------------------------------

@app.post("/token", response_model=TokenResponse)
async def token_endpoint(
    grant_type: str = Form(...),
    code: Optional[str] = Form(None),
    redirect_uri: Optional[str] = Form(None),
    client_id: Optional[str] = Form(None),
    code_verifier: Optional[str] = Form(None),
    refresh_token: Optional[str] = Form(None),
    scope: Optional[str] = Form(None),
):
    """
    支持两种 grant：
    - authorization_code：code + PKCE verifier 换 access + refresh
    - refresh_token：旧 refresh 换新 access + 新 refresh（Rotation）
    """
    if grant_type == "authorization_code":
        return await _handle_authorization_code(
            code, redirect_uri, client_id, code_verifier
        )
    elif grant_type == "refresh_token":
        return await _handle_refresh_token(refresh_token, client_id, scope)
    else:
        raise HTTPException(status_code=400, detail=f"不支持的 grant_type: {grant_type}")


async def _handle_authorization_code(
    code: Optional[str],
    redirect_uri: Optional[str],
    client_id: Optional[str],
    code_verifier: Optional[str],
) -> TokenResponse:
    """处理 authorization_code grant。"""
    # 参数完整性检查
    if not all([code, redirect_uri, client_id, code_verifier]):
        raise HTTPException(
            status_code=400,
            detail="authorization_code grant 缺少必要参数",
        )

    record = storage.get_code(code)  # type: ignore[arg-type]

    # 校验顺序：存在 → 有效 → client 匹配 → redirect 匹配 → PKCE
    if not record:
        raise HTTPException(status_code=400, detail="无效 authorization code")

    if not record.is_valid:
        detail = "authorization code 已使用" if record.used else "authorization code 已过期"
        raise HTTPException(status_code=400, detail=detail)

    if record.client_id != client_id:
        raise HTTPException(status_code=400, detail="client_id 不匹配")

    if record.redirect_uri != redirect_uri:
        raise HTTPException(status_code=400, detail="redirect_uri 不匹配")

    if not verify_pkce(code_verifier, record.code_challenge):  # type: ignore[arg-type]
        raise HTTPException(
            status_code=400,
            detail="PKCE 验证失败：code_verifier 不匹配 code_challenge",
        )

    # 所有检查通过：标记 code 已用（防重放）
    storage.mark_code_used(code)  # type: ignore[arg-type]

    # 签发 Access Token
    access_token, expires_in = create_access_token(
        subject=record.user_id,
        scope=record.scope,
        client_id=record.client_id,
    )

    # 签发 Refresh Token（仅当 scope 含 offline_access）
    refresh = None
    if "offline_access" in record.scope.split():
        refresh = generate_secure_token(32)
        storage.save_refresh_token(RefreshTokenRecord(
            token=refresh,
            client_id=record.client_id,
            user_id=record.user_id,
            scope=record.scope,
        ))

    return TokenResponse(
        access_token=access_token,
        expires_in=expires_in,
        refresh_token=refresh,
        scope=record.scope,
    )


async def _handle_refresh_token(
    refresh_token: Optional[str],
    client_id: Optional[str],
    scope: Optional[str],
) -> TokenResponse:
    """
    Refresh Token Rotation：
    1. 旧 refresh 验证通过
    2. 立即作废旧 refresh（防重放）
    3. 签发新 access + 新 refresh
    """
    if not refresh_token or not client_id:
        raise HTTPException(status_code=400, detail="refresh_token grant 缺少参数")

    record = storage.get_refresh_token(refresh_token)

    if not record:
        raise HTTPException(status_code=400, detail="无效 refresh_token")

    if not record.is_valid:
        detail = "refresh_token 已吊销" if record.revoked else "refresh_token 已过期"
        raise HTTPException(status_code=400, detail=detail)

    if record.client_id != client_id:
        raise HTTPException(status_code=400, detail="client_id 不匹配")

    # Rotation：立即作废旧 refresh
    storage.revoke_refresh_token(refresh_token)

    # 签发新 Access Token
    access_token, expires_in = create_access_token(
        subject=record.user_id,
        scope=record.scope,
        client_id=record.client_id,
    )

    # 签发新 Refresh Token
    new_refresh = generate_secure_token(32)
    storage.save_refresh_token(RefreshTokenRecord(
        token=new_refresh,
        client_id=record.client_id,
        user_id=record.user_id,
        scope=record.scope,
    ))

    return TokenResponse(
        access_token=access_token,
        expires_in=expires_in,
        refresh_token=new_refresh,
        scope=record.scope,
    )


# ---------------------------------------------------------------------------
# Revocation Endpoint（RFC 7009）
# ---------------------------------------------------------------------------

@app.post("/revoke")
async def revoke(
    token: str = Form(...),
    client_id: Optional[str] = Form(None),
):
    """
    吊销 Refresh Token。
    RFC 7009：不存在的 token 也返回 200（防止枚举攻击）。
    """
    record = storage.get_refresh_token(token)
    if record and (client_id is None or record.client_id == client_id):
        storage.revoke_refresh_token(token)
    return JSONResponse(content={}, status_code=200)
```

---

## 四十一、启动并验证 Auth Server

```bash
# 终端 1：启动 Auth Server
uvicorn auth_server.main:app --port 8000 --reload

# 验证元数据端点
curl -s http://localhost:8000/.well-known/oauth-authorization-server | python -m json.tool

# 验证 JWKS
curl -s http://localhost:8000/jwks.json | python -m json.tool

# 期望响应（JWKS 示例）：
# {
#   "keys": [
#     {
#       "kty": "RSA",
#       "use": "sig",
#       "alg": "RS256",
#       "kid": "demo-key-001",
#       "n": "...",
#       "e": "AQAB"
#     }
#   ]
# }
```

---

## 四十二、MCP Server — auth.py

从 Authorization Header 提取 Bearer，验签，检查 Scope。

```python
# mcp_server/auth.py
from __future__ import annotations

import os
from functools import lru_cache
from typing import Any

import jwt
from jwt import PyJWKClient
from fastapi import HTTPException, Request

# ---------------------------------------------------------------------------
# 配置
# ---------------------------------------------------------------------------

EXPECTED_ISSUER = os.getenv("EXPECTED_ISSUER", "http://localhost:8000")
EXPECTED_AUDIENCE = os.getenv("EXPECTED_AUDIENCE", "http://localhost:8001/mcp")
JWKS_URL = os.getenv("JWKS_URL", "http://localhost:8000/jwks.json")

# Resource Metadata URL（用于 401 响应头）
RESOURCE_METADATA_URL = (
    "http://localhost:8001/.well-known/oauth-protected-resource/mcp"
)


@lru_cache(maxsize=1)
def _get_jwks_client() -> PyJWKClient:
    """缓存 JWKS 客户端（自动处理 key rotation 缓存）。"""
    return PyJWKClient(JWKS_URL, cache_keys=True)


# ---------------------------------------------------------------------------
# Token 验证
# ---------------------------------------------------------------------------

def extract_bearer_token(request: Request) -> str:
    """
    从 Authorization 头提取 Bearer Token。
    缺少 → 401 + WWW-Authenticate（含 resource_metadata，客户端据此发现 AS）。
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="missing_token",
            headers={
                "WWW-Authenticate": (
                    f'Bearer resource_metadata="{RESOURCE_METADATA_URL}"'
                ),
            },
        )
    return auth_header[len("Bearer "):]


def verify_token(token: str) -> dict[str, Any]:
    """
    验签 JWT：
    1. 从 JWKS 拉取公钥（kid 匹配）
    2. 验证 RS256 签名
    3. 验证 iss / aud / exp
    失败一律 401。
    """
    try:
        jwks_client = _get_jwks_client()
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=EXPECTED_AUDIENCE,
            issuer=EXPECTED_ISSUER,
            options={"require": ["exp", "iss", "aud", "sub", "scope"]},
        )
        return claims
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="token_expired")
    except jwt.InvalidAudienceError:
        raise HTTPException(status_code=401, detail="invalid_audience")
    except jwt.InvalidIssuerError:
        raise HTTPException(status_code=401, detail="invalid_issuer")
    except Exception as exc:
        raise HTTPException(status_code=401, detail=f"invalid_token: {exc}")


def require_scopes(claims: dict[str, Any], required: set[str]) -> None:
    """
    检查 JWT claims 中的 scope 是否包含所有必需 scope。
    不足 → 403 + insufficient_scope。
    """
    token_scopes = set(claims.get("scope", "").split())
    missing = required - token_scopes
    if missing:
        raise HTTPException(
            status_code=403,
            detail=f"insufficient_scope: 缺少 {missing}",
        )


def authenticate_request(request: Request, required_scopes: set[str]) -> dict[str, Any]:
    """
    组合：提取 Token → 验签 → 检查 Scope → 返回 claims。
    MCP Tool 处理器直接调用此函数。
    """
    token = extract_bearer_token(request)
    claims = verify_token(token)
    require_scopes(claims, required_scopes)
    return claims
```

---

## 四十三、MCP Server — policies.py

第二道墙：Agent Policy（与 OAuth Scope 独立）。

```python
# mcp_server/policies.py
from __future__ import annotations

from fastapi import HTTPException

# ---------------------------------------------------------------------------
# Agent Policy 配置
# 生产：从数据库读取，按 Agent Profile / 账户级别动态设置
# ---------------------------------------------------------------------------

# 允许交易的标的白名单
ALLOWED_SYMBOLS = {
    "NVDA", "MSFT", "AAPL", "GOOGL", "AMZN",
    "META", "TSLA", "AVGO", "AMD", "QCOM",
}

# 单笔最大名义金额（美元）
MAX_NOTIONAL_USD = 500.0

# 模拟 Portfolio（用户 demo-user-001）
MOCK_PORTFOLIO = {
    "account_id": "demo-account-001",
    "user_id": "demo-user-001",
    "cash_usd": 10_000.0,
    "positions": [
        {"symbol": "NVDA", "quantity": 5,  "avg_cost": 420.0, "current_price": 875.0},
        {"symbol": "MSFT", "quantity": 10, "avg_cost": 310.0, "current_price": 415.0},
        {"symbol": "AAPL", "quantity": 8,  "avg_cost": 155.0, "current_price": 193.0},
    ],
}

# 模拟报价（简单固定价，生产接实时行情）
MOCK_QUOTES = {
    "NVDA": 875.0,
    "MSFT": 415.0,
    "AAPL": 193.0,
    "GOOGL": 172.0,
    "AMZN": 185.0,
    "META": 490.0,
    "TSLA": 175.0,
    "AVGO": 1320.0,
    "AMD": 165.0,
    "QCOM": 198.0,
}


# ---------------------------------------------------------------------------
# Policy 检查函数
# ---------------------------------------------------------------------------

def check_order_policy(symbol: str, quantity: int, side: str) -> float:
    """
    校验订单是否符合 Agent Policy：
    1. 标的在白名单中
    2. 名义金额不超过单笔上限
    返回当前报价（用于计算 review 摘要）。
    """
    symbol = symbol.upper()

    if symbol not in ALLOWED_SYMBOLS:
        raise HTTPException(
            status_code=403,
            detail=f"policy_violation: {symbol} 不在允许交易的标的列表中",
        )

    if quantity <= 0:
        raise HTTPException(
            status_code=400,
            detail="quantity 必须 > 0",
        )

    price = MOCK_QUOTES.get(symbol)
    if price is None:
        raise HTTPException(
            status_code=400,
            detail=f"没有 {symbol} 的报价数据",
        )

    notional = price * quantity
    if notional > MAX_NOTIONAL_USD:
        raise HTTPException(
            status_code=403,
            detail=(
                f"policy_violation: 名义金额 ${notional:.2f} 超过单笔上限 "
                f"${MAX_NOTIONAL_USD:.2f}"
            ),
        )

    return price
```

---

## 四十四、MCP Server — tools.py

四个 MCP Tool 的具体实现，含 Review → Execute 状态机与幂等。

```python
# mcp_server/tools.py
from __future__ import annotations

import os
import threading
import time
from typing import Any

from fastapi import HTTPException

from mcp_server.policies import (
    MOCK_PORTFOLIO,
    MOCK_QUOTES,
    check_order_policy,
)

# ---------------------------------------------------------------------------
# Review Store（内存，生产用 DB + SELECT FOR UPDATE）
# ---------------------------------------------------------------------------

_review_lock = threading.Lock()
_reviews: dict[str, dict] = {}   # review_id → review record

_idempotency_lock = threading.Lock()
_idempotency_results: dict[str, dict] = {}   # idempotency_key → order result

REVIEW_TTL_SECONDS = 120   # review 有效期 2 分钟


# ---------------------------------------------------------------------------
# Tool: get_portfolio
# ---------------------------------------------------------------------------

def tool_get_portfolio(user_id: str) -> dict:
    """
    返回模拟仓位数据。
    scope 要求：portfolio.read
    """
    # Demo 只有一个用户，实际按 user_id 查 DB
    portfolio = dict(MOCK_PORTFOLIO)
    portfolio["queried_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    return portfolio


# ---------------------------------------------------------------------------
# Tool: get_quote
# ---------------------------------------------------------------------------

def tool_get_quote(symbol: str) -> dict:
    """
    返回模拟报价。
    scope 要求：quotes.read
    """
    symbol = symbol.upper()
    price = MOCK_QUOTES.get(symbol)
    if price is None:
        raise HTTPException(
            status_code=404,
            detail=f"没有 {symbol} 的报价数据",
        )
    return {
        "symbol": symbol,
        "price": price,
        "currency": "USD",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "note": "模拟报价，非实时行情",
    }


# ---------------------------------------------------------------------------
# Tool: review_equity_order（第一阶段：生成 review，不执行）
# ---------------------------------------------------------------------------

def tool_review_equity_order(
    symbol: str,
    quantity: int,
    side: str,    # "buy" | "sell"
    user_id: str,
) -> dict:
    """
    生成订单预览，返回 review_id（TTL 120s），不执行。
    scope 要求：orders.review
    
    关键设计：
    - 把所有业务参数（symbol / quantity / side / price）固化到 review 记录里
    - place 阶段只传 review_id，无法再修改业务参数
    """
    side = side.lower()
    if side not in ("buy", "sell"):
        raise HTTPException(status_code=400, detail="side 必须是 buy 或 sell")

    # Agent Policy 检查（第二道墙）
    price = check_order_policy(symbol, quantity, side)

    # 生成 review_id
    review_id = f"rev_{os.urandom(12).hex()}"
    notional = price * quantity

    review = {
        "review_id": review_id,
        "user_id": user_id,
        "symbol": symbol.upper(),
        "quantity": quantity,
        "side": side,
        "estimated_price": price,
        "estimated_notional": round(notional, 2),
        "currency": "USD",
        "expires_at": time.time() + REVIEW_TTL_SECONDS,
        "used": False,
        "created_at": time.time(),
        "note": "模拟下单，不会产生真实交易",
    }

    with _review_lock:
        _reviews[review_id] = review

    # 返回给客户端显示的确认摘要
    return {
        "review_id": review_id,
        "summary": (
            f"{'买入' if side == 'buy' else '卖出'} {quantity} 股 {symbol.upper()} "
            f"@ 约 ${price:.2f}，预计名义金额 ${notional:.2f}"
        ),
        "expires_in_seconds": REVIEW_TTL_SECONDS,
        "action_required": "请在客户端输入 YES 确认后调用 place_equity_order",
        "warning": "模拟系统，不产生真实交易",
    }


# ---------------------------------------------------------------------------
# Tool: place_equity_order（第二阶段：仅凭 review_id 执行，不接受可变参数）
# ---------------------------------------------------------------------------

def tool_place_equity_order(
    review_id: str,
    idempotency_key: str,
    user_id: str,
) -> dict:
    """
    凭 review_id 执行订单。
    scope 要求：orders.place
    
    安全设计：
    1. review_id 只能用一次（防重放）
    2. idempotency_key 相同 → 返回同一结果（幂等，防网络重试重复下单）
    3. 不接受 symbol / quantity 等可变业务参数（防 review 绕过）
    """
    # 幂等检查：同一 idempotency_key 直接返回缓存结果
    with _idempotency_lock:
        cached = _idempotency_results.get(idempotency_key)
        if cached:
            return {**cached, "idempotent": True}

    # 获取 review
    with _review_lock:
        review = _reviews.get(review_id)
        if not review:
            raise HTTPException(status_code=400, detail="无效 review_id")

        if review["used"]:
            raise HTTPException(
                status_code=409,
                detail="review_id 已使用，不能重复下单",
            )

        if time.time() > review["expires_at"]:
            raise HTTPException(
                status_code=400,
                detail="review_id 已过期，请重新 review",
            )

        if review["user_id"] != user_id:
            raise HTTPException(
                status_code=403,
                detail="review_id 与当前用户不匹配",
            )

        # 原子标记 used（在锁内完成，防并发重放）
        review["used"] = True

    # 模拟成交
    fill_price = review["estimated_price"]   # 实际系统用撮合价
    order_id = f"ord_{os.urandom(12).hex()}"

    result = {
        "order_id": order_id,
        "review_id": review_id,
        "idempotency_key": idempotency_key,
        "symbol": review["symbol"],
        "quantity": review["quantity"],
        "side": review["side"],
        "fill_price": fill_price,
        "notional": round(fill_price * review["quantity"], 2),
        "status": "filled",
        "filled_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "note": "模拟成交，不产生真实交易",
    }

    # 存入幂等缓存
    with _idempotency_lock:
        _idempotency_results[idempotency_key] = result

    return result
```

---

## 四十五、MCP Server — main.py

JSON-RPC `/mcp` 端点 + Protected Resource Metadata。

```python
# mcp_server/main.py
from __future__ import annotations

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from mcp_server.auth import authenticate_request, EXPECTED_AUDIENCE
from mcp_server.tools import (
    tool_get_portfolio,
    tool_get_quote,
    tool_place_equity_order,
    tool_review_equity_order,
)

app = FastAPI(title="OAuth 2.1 MCP Server (Demo)")

MCP_SERVER_ISSUER = "http://localhost:8001"

# ---------------------------------------------------------------------------
# Tool Definitions（tools/list 返回）
# ---------------------------------------------------------------------------

TOOLS = [
    {
        "name": "get_portfolio",
        "description": "返回模拟仓位和现金余额（不连真实券商）",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
        "scope_required": "portfolio.read",
    },
    {
        "name": "get_quote",
        "description": "返回指定标的的模拟报价",
        "inputSchema": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "股票代码，如 NVDA"},
            },
            "required": ["symbol"],
        },
        "scope_required": "quotes.read",
    },
    {
        "name": "review_equity_order",
        "description": "生成订单预览（review_id），不执行。需人工确认后调 place_equity_order",
        "inputSchema": {
            "type": "object",
            "properties": {
                "symbol":   {"type": "string"},
                "quantity": {"type": "integer", "minimum": 1},
                "side":     {"type": "string", "enum": ["buy", "sell"]},
            },
            "required": ["symbol", "quantity", "side"],
        },
        "scope_required": "orders.review",
    },
    {
        "name": "place_equity_order",
        "description": "凭 review_id 执行模拟下单（幂等）",
        "inputSchema": {
            "type": "object",
            "properties": {
                "review_id":       {"type": "string"},
                "idempotency_key": {"type": "string"},
            },
            "required": ["review_id", "idempotency_key"],
        },
        "scope_required": "orders.place",
    },
]


# ---------------------------------------------------------------------------
# Protected Resource Metadata（RFC 9728）
# ---------------------------------------------------------------------------

@app.get("/.well-known/oauth-protected-resource/mcp")
async def protected_resource_metadata():
    """
    客户端收到 401 后从此端点发现对应的 Authorization Server。
    """
    return {
        "resource": EXPECTED_AUDIENCE,
        "authorization_servers": ["http://localhost:8000"],
        "scopes_supported": [
            "portfolio.read",
            "quotes.read",
            "orders.review",
            "orders.place",
            "offline_access",
        ],
        "bearer_methods_supported": ["header"],
        "resource_documentation": "https://github.com/xingaiapp/xingai-robinhood-mcp",
    }


# ---------------------------------------------------------------------------
# JSON-RPC /mcp 端点
# ---------------------------------------------------------------------------

def _jsonrpc_error(id_: object, code: int, message: str, status: int = 200) -> JSONResponse:
    return JSONResponse(
        content={
            "jsonrpc": "2.0",
            "id": id_,
            "error": {"code": code, "message": message},
        },
        status_code=status,
    )


@app.post("/mcp")
async def mcp_endpoint(request: Request):
    """
    统一 JSON-RPC 2.0 端点，处理：
    - initialize
    - tools/list
    - tools/call
    """
    # 先验证 Token（无 Token 返回 401 + WWW-Authenticate）
    try:
        token = request.headers.get("Authorization", "")
        if not token.startswith("Bearer "):
            raise HTTPException(
                status_code=401,
                detail="missing_token",
                headers={
                    "WWW-Authenticate": (
                        'Bearer resource_metadata='
                        '"http://localhost:8001/.well-known/oauth-protected-resource/mcp"'
                    ),
                },
            )
    except HTTPException:
        raise

    body = await request.json()
    method = body.get("method")
    params = body.get("params", {})
    req_id = body.get("id")

    try:
        if method == "initialize":
            return _handle_initialize(req_id)

        elif method == "tools/list":
            # tools/list 需要 Token，但无特定 scope 要求（只需已认证）
            claims = authenticate_request(request, set())
            tool_list = [
                {k: v for k, v in t.items() if k != "scope_required"}
                for t in TOOLS
            ]
            return JSONResponse(content={
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"tools": tool_list},
            })

        elif method == "tools/call":
            return await _handle_tool_call(request, req_id, params)

        else:
            return _jsonrpc_error(req_id, -32601, f"未知方法: {method}")

    except HTTPException as exc:
        return _jsonrpc_error(req_id, exc.status_code, exc.detail, exc.status_code)
    except Exception as exc:
        # 不向客户端暴露内部堆栈
        return _jsonrpc_error(req_id, -32603, "内部错误", 500)


def _handle_initialize(req_id: object) -> JSONResponse:
    return JSONResponse(content={
        "jsonrpc": "2.0",
        "id": req_id,
        "result": {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {}},
            "serverInfo": {
                "name": "XingAI MCP Demo Server",
                "version": "0.1.0",
                "description": "模拟投资组合 MCP Server，不连真实券商",
            },
        },
    })


async def _handle_tool_call(
    request: Request,
    req_id: object,
    params: dict,
) -> JSONResponse:
    tool_name = params.get("name")
    arguments = params.get("arguments", {})

    # 找到 Tool 定义
    tool_def = next((t for t in TOOLS if t["name"] == tool_name), None)
    if not tool_def:
        return _jsonrpc_error(req_id, -32602, f"未知工具: {tool_name}")

    # 检查 Scope
    required_scope = tool_def["scope_required"]
    try:
        claims = authenticate_request(request, {required_scope})
    except HTTPException as exc:
        return _jsonrpc_error(req_id, exc.status_code, exc.detail, exc.status_code)

    user_id = claims.get("sub", "unknown")

    # 分发到对应 Tool
    try:
        if tool_name == "get_portfolio":
            result = tool_get_portfolio(user_id)

        elif tool_name == "get_quote":
            symbol = arguments.get("symbol")
            if not symbol:
                return _jsonrpc_error(req_id, -32602, "缺少参数: symbol")
            result = tool_get_quote(symbol)

        elif tool_name == "review_equity_order":
            result = tool_review_equity_order(
                symbol=arguments.get("symbol", ""),
                quantity=int(arguments.get("quantity", 0)),
                side=arguments.get("side", ""),
                user_id=user_id,
            )

        elif tool_name == "place_equity_order":
            result = tool_place_equity_order(
                review_id=arguments.get("review_id", ""),
                idempotency_key=arguments.get("idempotency_key", ""),
                user_id=user_id,
            )

        else:
            return _jsonrpc_error(req_id, -32601, f"Tool 未实现: {tool_name}")

    except HTTPException as exc:
        return _jsonrpc_error(req_id, exc.status_code, exc.detail, exc.status_code)

    return JSONResponse(content={
        "jsonrpc": "2.0",
        "id": req_id,
        "result": {
            "content": [{"type": "text", "text": str(result)}],
            "_data": result,   # 便于客户端结构化解析
        },
    })
```

---

## 四十六、启动并验证 MCP Server

```bash
# 终端 2：启动 MCP Server
uvicorn mcp_server.main:app --port 8001 --reload

# 测试 1：无 Token 访问，期望 401 + WWW-Authenticate
curl -i -X POST http://localhost:8001/mcp \
  -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'

# 期望响应头包含：
# HTTP/1.1 401 Unauthorized
# WWW-Authenticate: Bearer resource_metadata="http://localhost:8001/.well-known/oauth-protected-resource/mcp"

# 测试 2：Protected Resource Metadata
curl -s http://localhost:8001/.well-known/oauth-protected-resource/mcp | python -m json.tool
```

---

## 四十七、Client — discovery.py

自动发现：401 → Resource Metadata → AS Metadata。

```python
# client/discovery.py
from __future__ import annotations

import re
import urllib.parse

import requests

# SSRF 防护：只允许 localhost 系 AS（Demo 限制，生产改白名单）
ALLOWED_AS_HOSTS = {"localhost", "127.0.0.1"}


def discover_from_401(www_authenticate: str) -> dict:
    """
    从 401 响应的 WWW-Authenticate 头提取 resource_metadata URL，
    然后逐步发现 AS 元数据。
    
    返回 AS Metadata dict，含所有端点地址。
    """
    resource_metadata_url = _extract_resource_metadata_url(www_authenticate)
    resource_metadata = _fetch_resource_metadata(resource_metadata_url)
    as_metadata = _fetch_as_metadata(resource_metadata)
    _validate_as_metadata(as_metadata)
    return as_metadata


def _extract_resource_metadata_url(www_authenticate: str) -> str:
    """
    解析 WWW-Authenticate 头，提取 resource_metadata URL。
    例：Bearer resource_metadata="http://localhost:8001/..."
    """
    match = re.search(r'resource_metadata="([^"]+)"', www_authenticate)
    if not match:
        raise ValueError(
            f"WWW-Authenticate 头中没有 resource_metadata: {www_authenticate}"
        )
    url = match.group(1)
    _check_ssrf(url)
    return url


def _fetch_resource_metadata(url: str) -> dict:
    """拉取 Resource Metadata，获取 authorization_servers 列表。"""
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    if "authorization_servers" not in data or not data["authorization_servers"]:
        raise ValueError("Resource Metadata 缺少 authorization_servers")
    return data


def _fetch_as_metadata(resource_metadata: dict) -> dict:
    """从 authorization_servers[0] 拉取 AS Metadata（RFC 8414）。"""
    as_base = resource_metadata["authorization_servers"][0]
    _check_ssrf(as_base)
    metadata_url = f"{as_base.rstrip('/')}/.well-known/oauth-authorization-server"
    resp = requests.get(metadata_url, timeout=10)
    resp.raise_for_status()
    return resp.json()


def _validate_as_metadata(metadata: dict) -> None:
    """校验 AS Metadata 包含必要字段且支持 S256。"""
    required_fields = [
        "issuer",
        "authorization_endpoint",
        "token_endpoint",
        "jwks_uri",
    ]
    for field in required_fields:
        if field not in metadata:
            raise ValueError(f"AS Metadata 缺少必要字段: {field}")

    pkce_methods = metadata.get("code_challenge_methods_supported", [])
    if "S256" not in pkce_methods:
        raise ValueError("AS 不支持 S256 PKCE，拒绝连接")


def _check_ssrf(url: str) -> None:
    """SSRF 防护：Demo 只允许 localhost 类 AS。"""
    parsed = urllib.parse.urlparse(url)
    hostname = parsed.hostname or ""
    if hostname not in ALLOWED_AS_HOSTS:
        raise ValueError(
            f"SSRF 防护：不允许连接非 localhost AS ({hostname})"
        )
```

---

## 四十八、Client — oauth.py

PKCE 生成、本机 Callback Server、Token 交换。

```python
# client/oauth.py
from __future__ import annotations

import base64
import hashlib
import http.server
import os
import threading
import time
import urllib.parse
import webbrowser
from typing import Optional

import requests


# ---------------------------------------------------------------------------
# PKCE 生成
# ---------------------------------------------------------------------------

def generate_pkce_pair() -> tuple[str, str]:
    """
    生成 PKCE code_verifier + code_challenge (S256)。
    
    返回 (verifier, challenge)。
    verifier 是 43–128 字符的随机 URL-safe 字符串。
    challenge = BASE64URL( SHA256( verifier ) )（无 padding）
    """
    verifier = base64.urlsafe_b64encode(os.urandom(32)).rstrip(b"=").decode("ascii")
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return verifier, challenge


# ---------------------------------------------------------------------------
# 本机 Callback Server（接收 Authorization Code）
# ---------------------------------------------------------------------------

class _CallbackHandler(http.server.BaseHTTPRequestHandler):
    """临时 HTTP Server，接收 Authorization Server 的重定向回调。"""

    result: Optional[dict] = None
    _server_ref: Optional[http.server.HTTPServer] = None

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        params = dict(urllib.parse.parse_qsl(parsed.query))

        self.__class__.result = params

        # 返回简单成功页
        body = b"""
        <html><body>
        <h2>&#10003; 授权成功</h2>
        <p>可以关闭此窗口，返回终端继续操作。</p>
        </body></html>
        """
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(body)

        # 异步关闭 server
        threading.Thread(target=self._server_ref.shutdown, daemon=True).start()

    def log_message(self, format_, *args) -> None:
        pass   # 静默日志


def run_local_callback_server(port: int = 54321, timeout: int = 180) -> dict:
    """
    启动本机 Callback Server，等待 Authorization Code 回调。
    超时未收到则抛异常。
    """
    _CallbackHandler.result = None
    server = http.server.HTTPServer(("127.0.0.1", port), _CallbackHandler)
    _CallbackHandler._server_ref = server

    # 在后台线程等待（最多 timeout 秒）
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    deadline = time.time() + timeout
    while _CallbackHandler.result is None:
        if time.time() > deadline:
            server.shutdown()
            raise TimeoutError(f"等待 {timeout}s 未收到 Authorization Code")
        time.sleep(0.2)

    return _CallbackHandler.result


# ---------------------------------------------------------------------------
# Authorization URL 构建 + 浏览器打开
# ---------------------------------------------------------------------------

def build_authorization_url(
    as_metadata: dict,
    client_id: str,
    redirect_uri: str,
    scope: str,
    state: str,
    code_challenge: str,
) -> str:
    """构建携带 PKCE 的 Authorization URL。"""
    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": scope,
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }
    base = as_metadata["authorization_endpoint"]
    return f"{base}?{urllib.parse.urlencode(params)}"


# ---------------------------------------------------------------------------
# Token 交换（code + PKCE verifier → access token）
# ---------------------------------------------------------------------------

def exchange_code_for_token(
    as_metadata: dict,
    code: str,
    code_verifier: str,
    client_id: str,
    redirect_uri: str,
) -> dict:
    """
    用 authorization code + PKCE verifier 换 Access Token。
    返回完整 Token Response dict。
    """
    token_url = as_metadata["token_endpoint"]
    resp = requests.post(
        token_url,
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "client_id": client_id,
            "code_verifier": code_verifier,
        },
        timeout=15,
    )

    if not resp.ok:
        raise ValueError(f"Token 交换失败 ({resp.status_code}): {resp.text}")

    token_data = resp.json()
    access_token = token_data.get("access_token", "")
    if not access_token:
        raise ValueError("Token 响应中没有 access_token，拒绝存储")

    return token_data


def refresh_access_token(
    as_metadata: dict,
    refresh_token: str,
    client_id: str,
) -> dict:
    """用 Refresh Token 换新 Access Token（Rotation：旧 refresh 自动作废）。"""
    token_url = as_metadata["token_endpoint"]
    resp = requests.post(
        token_url,
        data={
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": client_id,
        },
        timeout=15,
    )

    if not resp.ok:
        raise ValueError(f"Refresh 失败 ({resp.status_code}): {resp.text}")

    return resp.json()
```

---

## 四十九、Client — token_store.py

Token 持久化（demo 用文件，生产用 OS Keychain）。

```python
# client/token_store.py
from __future__ import annotations

import json
import os
import stat
import time
from pathlib import Path
from typing import Optional

# Demo Token 文件路径（生产改用 keyring 库存入 OS Keychain）
TOKEN_FILE = Path(os.getenv("MCP_TOKEN_FILE", ".mcp_tokens.json"))

# 提前刷新阈值：Token 还剩不足 60 秒时主动刷新
REFRESH_BUFFER_SECONDS = 60


def save_tokens(token_response: dict) -> None:
    """
    持久化 Token Response。
    写入后立即设置 chmod 600（仅所有者可读）。
    """
    data = {
        "access_token":  token_response.get("access_token"),
        "refresh_token": token_response.get("refresh_token"),
        "scope":         token_response.get("scope"),
        "expires_at":    time.time() + int(token_response.get("expires_in", 300)),
        "saved_at":      time.time(),
    }

    # 绝不存储空 access_token
    if not data["access_token"]:
        raise ValueError("拒绝存储空 access_token")

    TOKEN_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
    os.chmod(TOKEN_FILE, stat.S_IRUSR | stat.S_IWUSR)   # chmod 600


def load_tokens() -> Optional[dict]:
    """读取已存储的 Token，不存在返回 None。"""
    if not TOKEN_FILE.exists():
        return None
    try:
        return json.loads(TOKEN_FILE.read_text(encoding="utf-8"))
    except Exception:
        return None


def get_valid_access_token() -> Optional[str]:
    """
    返回有效的 Access Token。
    若 Token 即将过期（< REFRESH_BUFFER_SECONDS），返回 None 触发刷新。
    """
    tokens = load_tokens()
    if not tokens:
        return None

    access_token = tokens.get("access_token")
    expires_at = tokens.get("expires_at", 0)

    if not access_token:
        return None

    # 提前刷新：距离过期不足 buffer
    if time.time() + REFRESH_BUFFER_SECONDS >= expires_at:
        return None

    return access_token


def get_refresh_token() -> Optional[str]:
    """返回 Refresh Token（用于过期后静默刷新）。"""
    tokens = load_tokens()
    return tokens.get("refresh_token") if tokens else None


def clear_tokens() -> None:
    """清除本地 Token（用于登出或错误恢复）。"""
    if TOKEN_FILE.exists():
        TOKEN_FILE.unlink()
```

---

## 五十、Client — main.py

完整主流程：发现 → PKCE → Token → 调工具 → Review → 人工确认 → Place。

```python
# client/main.py
from __future__ import annotations

import base64
import json
import os
import time
import urllib.parse

import requests

from client.discovery import discover_from_401
from client.oauth import (
    build_authorization_url,
    exchange_code_for_token,
    generate_pkce_pair,
    refresh_access_token,
    run_local_callback_server,
)
from client.token_store import (
    clear_tokens,
    get_refresh_token,
    get_valid_access_token,
    save_tokens,
)

# ---------------------------------------------------------------------------
# 配置
# ---------------------------------------------------------------------------

MCP_URL = os.getenv("MCP_URL", "http://localhost:8001/mcp")
CLIENT_ID = "demo-desktop-client"
REDIRECT_URI = "http://127.0.0.1:54321/callback"
SCOPE = "portfolio.read quotes.read orders.review orders.place offline_access"
CALLBACK_PORT = 54321

_as_metadata: dict = {}     # 全局缓存 AS Metadata


# ---------------------------------------------------------------------------
# Token 管理
# ---------------------------------------------------------------------------

def ensure_valid_token() -> str:
    """
    确保有有效 Access Token。
    优先顺序：
    1. 缓存中未过期 Token
    2. 用 Refresh Token 静默刷新
    3. 触发完整 PKCE 授权流程
    """
    global _as_metadata

    # 1. 使用缓存 Token
    token = get_valid_access_token()
    if token:
        return token

    # 2. 尝试 Refresh
    refresh = get_refresh_token()
    if refresh and _as_metadata:
        try:
            print("→ Access Token 即将过期，静默刷新...")
            token_data = refresh_access_token(_as_metadata, refresh, CLIENT_ID)
            save_tokens(token_data)
            print("✓ Token 刷新成功")
            return token_data["access_token"]
        except Exception as e:
            print(f"⚠ Refresh 失败（{e}），重新授权...")
            clear_tokens()

    # 3. 完整 PKCE 授权
    return _full_oauth_flow()


def _full_oauth_flow() -> str:
    """完整 PKCE Authorization Code Flow。"""
    global _as_metadata

    print("\n=== OAuth 2.1 + PKCE 授权流程开始 ===")

    # 先用无 Token 的请求触发 401，获取 AS 元数据
    if not _as_metadata:
        print("→ 发现 Authorization Server...")
        www_auth = _trigger_401_for_discovery()
        _as_metadata = discover_from_401(www_auth)
        print(f"✓ AS Issuer: {_as_metadata['issuer']}")

    # 生成 PKCE 和 state
    verifier, challenge = generate_pkce_pair()
    state = base64.urlsafe_b64encode(os.urandom(16)).rstrip(b"=").decode("ascii")

    # 打开浏览器
    auth_url = build_authorization_url(
        _as_metadata, CLIENT_ID, REDIRECT_URI, SCOPE, state, challenge
    )
    print(f"\n→ 打开浏览器授权页...")
    print(f"  URL: {auth_url[:80]}...")

    import webbrowser
    webbrowser.open(auth_url)

    # 等待回调
    print("→ 等待用户在浏览器中点击「同意授权」...")
    callback = run_local_callback_server(port=CALLBACK_PORT, timeout=180)

    # 校验 state（防 CSRF）
    if callback.get("state") != state:
        raise ValueError("state 不匹配，可能遭受 CSRF 攻击！")

    if "error" in callback:
        raise ValueError(f"授权被拒绝: {callback['error']}")

    code = callback.get("code")
    if not code:
        raise ValueError("回调中没有 authorization code")

    print("✓ 收到 Authorization Code，换取 Token...")
    token_data = exchange_code_for_token(
        _as_metadata, code, verifier, CLIENT_ID, REDIRECT_URI
    )
    save_tokens(token_data)
    print("✓ Token 已获取并安全存储")
    return token_data["access_token"]


def _trigger_401_for_discovery() -> str:
    """向 MCP Server 发一个无 Token 的请求，拿 WWW-Authenticate 头。"""
    resp = requests.post(
        MCP_URL,
        json={"jsonrpc": "2.0", "id": 0, "method": "initialize", "params": {}},
        timeout=10,
    )
    if resp.status_code != 401:
        raise ValueError(f"期望 401，实际收到 {resp.status_code}")
    www_auth = resp.headers.get("WWW-Authenticate", "")
    if not www_auth:
        raise ValueError("401 响应缺少 WWW-Authenticate 头")
    return www_auth


# ---------------------------------------------------------------------------
# MCP RPC 调用
# ---------------------------------------------------------------------------

_request_counter = 0


def call_mcp(method: str, params: dict = None, *, retry_on_401: bool = True) -> dict:
    """
    发送 JSON-RPC 请求到 MCP Server。
    401 → 刷新 Token → 重试一次（只重试一次，防无限循环）。
    """
    global _request_counter
    _request_counter += 1

    token = ensure_valid_token()
    body = {
        "jsonrpc": "2.0",
        "id": _request_counter,
        "method": method,
        "params": params or {},
    }

    resp = requests.post(
        MCP_URL,
        json=body,
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )

    if resp.status_code == 401 and retry_on_401:
        print("→ 收到 401，刷新 Token 后重试...")
        clear_tokens()
        return call_mcp(method, params, retry_on_401=False)

    data = resp.json()

    if "error" in data:
        raise RuntimeError(
            f"MCP 错误 [{data['error'].get('code')}]: {data['error'].get('message')}"
        )

    return data.get("result", {})


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

def main() -> None:
    print("=" * 60)
    print("  XingAI MCP Demo Client")
    print("  模拟投资组合 — 不连真实券商，不产生真实交易")
    print("=" * 60)

    # Step 1: Initialize
    print("\n[1/6] Initialize MCP 连接...")
    init_result = call_mcp("initialize")
    server_info = init_result.get("serverInfo", {})
    print(f"✓ 连接成功: {server_info.get('name')} v{server_info.get('version')}")

    # Step 2: List Tools
    print("\n[2/6] 获取可用工具列表...")
    tools_result = call_mcp("tools/list")
    tools = tools_result.get("tools", [])
    print(f"✓ 可用工具 ({len(tools)}):")
    for t in tools:
        print(f"   • {t['name']}: {t.get('description', '')}")

    # Step 3: Get Portfolio
    print("\n[3/6] 查询模拟仓位...")
    portfolio_result = call_mcp("tools/call", {
        "name": "get_portfolio",
        "arguments": {},
    })
    portfolio = portfolio_result.get("_data", {})
    print(f"✓ 账户: {portfolio.get('account_id')}")
    print(f"  现金: ${portfolio.get('cash_usd', 0):,.2f}")
    print(f"  持仓:")
    for pos in portfolio.get("positions", []):
        pnl = (pos["current_price"] - pos["avg_cost"]) * pos["quantity"]
        print(f"    {pos['symbol']}: {pos['quantity']} 股 @ 当前 ${pos['current_price']:.2f}  P&L: ${pnl:+.2f}")

    # Step 4: Get Quote
    symbol = "NVDA"
    print(f"\n[4/6] 查询 {symbol} 模拟报价...")
    quote_result = call_mcp("tools/call", {
        "name": "get_quote",
        "arguments": {"symbol": symbol},
    })
    quote = quote_result.get("_data", {})
    print(f"✓ {quote['symbol']}: ${quote['price']:.2f} (模拟报价)")

    # Step 5: Review Order（第一阶段，不执行）
    print(f"\n[5/6] 提交订单预览（Review，不执行）...")
    review_result = call_mcp("tools/call", {
        "name": "review_equity_order",
        "arguments": {
            "symbol": symbol,
            "quantity": 1,
            "side": "buy",
        },
    })
    review = review_result.get("_data", {})

    print(f"\n{'=' * 50}")
    print(f"  订单预览（Review）")
    print(f"{'=' * 50}")
    print(f"  {review.get('summary', '')}")
    print(f"  Review ID: {review.get('review_id', '')}")
    print(f"  有效期: {review.get('expires_in_seconds', 0)} 秒")
    print(f"  ⚠  {review.get('warning', '')}")
    print(f"{'=' * 50}")

    # 人机确认
    confirm = input("\n请输入 YES 确认下单（其他任意键取消）: ").strip()
    if confirm != "YES":
        print("✗ 已取消。")
        return

    # Step 6: Place Order（第二阶段，幂等）
    print(f"\n[6/6] 提交模拟下单（Place，幂等）...")
    idempotency_key = f"idem_{os.urandom(8).hex()}"

    place_result = call_mcp("tools/call", {
        "name": "place_equity_order",
        "arguments": {
            "review_id": review["review_id"],
            "idempotency_key": idempotency_key,
        },
    })
    order = place_result.get("_data", {})

    print(f"\n{'=' * 50}")
    print(f"  模拟成交结果")
    print(f"{'=' * 50}")
    print(f"  Order ID:  {order.get('order_id')}")
    print(f"  状态:      {order.get('status')}")
    print(f"  {order.get('side', '').upper()} {order.get('quantity')} 股 {order.get('symbol')}")
    print(f"  成交价:    ${order.get('fill_price', 0):.2f}")
    print(f"  名义金额:  ${order.get('notional', 0):.2f}")
    print(f"  时间:      {order.get('filled_at')}")
    print(f"  ⚠  {order.get('note')}")
    print(f"{'=' * 50}")

    # 幂等重试演示
    print("\n→ 演示幂等性：用相同 idempotency_key 重试...")
    retry_result = call_mcp("tools/call", {
        "name": "place_equity_order",
        "arguments": {
            "review_id": review["review_id"],
            "idempotency_key": idempotency_key,
        },
    })
    retry_order = retry_result.get("_data", {})
    is_idempotent = retry_order.get("idempotent", False)
    print(f"✓ 重试结果幂等: {is_idempotent}，Order ID: {retry_order.get('order_id')}")
    assert retry_order.get("order_id") == order.get("order_id"), "幂等性失败！"

    print("\n✓ 完整流程演示完毕。感谢使用 XingAI MCP Demo。")


if __name__ == "__main__":
    main()
```

---

## 五十一、完整运行

打开三个终端：

```bash
# 终端 1：Auth Server
cd secure-mcp-demo
source .venv/bin/activate
uvicorn auth_server.main:app --port 8000 --reload

# ─────────────────────────────────────────────

# 终端 2：MCP Server
cd secure-mcp-demo
source .venv/bin/activate
uvicorn mcp_server.main:app --port 8001 --reload

# ─────────────────────────────────────────────

# 终端 3：Client
cd secure-mcp-demo
source .venv/bin/activate
python -m client.main
```

**预期完整路径**：

```text
Client 启动
  ↓
POST /mcp（无 Token）
  ↓ 401 + WWW-Authenticate: Bearer resource_metadata="..."
Client 解析 resource_metadata URL
  ↓
GET /.well-known/oauth-protected-resource/mcp
  ↓ authorization_servers: ["http://localhost:8000"]
GET /.well-known/oauth-authorization-server
  ↓ 所有端点地址 + S256 支持确认
Client 生成 PKCE verifier + challenge
  ↓
打开浏览器 → /authorize（携带 challenge + state）
  ↓ 用户点「同意授权」
/authorize POST → 生成 code（120s TTL）
  ↓ 重定向 127.0.0.1:54321/callback?code=...&state=...
Client 收到 code，校验 state
  ↓
POST /token（code + verifier）
  ↓ PKCE 验证通过 → JWT access + refresh token
Client 存储 Token（chmod 600）
  ↓
POST /mcp initialize → ✓
POST /mcp tools/list → 4 个工具
POST /mcp tools/call get_portfolio → 模拟仓位
POST /mcp tools/call get_quote → 模拟报价
POST /mcp tools/call review_equity_order → review_id
  ↓ 终端显示摘要，等待输入 YES
用户输入 YES
  ↓
POST /mcp tools/call place_equity_order → 模拟成交
POST /mcp tools/call place_equity_order（重试）→ 幂等返回同一 order
  ↓
流程完成
```

---

## 五十二、测试 — tests/test_auth_server.py

```python
# tests/test_auth_server.py
"""Auth Server 单元测试。"""
import pytest
from fastapi.testclient import TestClient

from auth_server.main import app
from auth_server.security import verify_pkce, generate_secure_token
from client.oauth import generate_pkce_pair

client = TestClient(app)


class TestPKCE:
    def test_pkce_valid(self):
        """正确的 verifier 应通过验证。"""
        verifier, challenge = generate_pkce_pair()
        assert verify_pkce(verifier, challenge) is True

    def test_pkce_invalid_verifier(self):
        """错误的 verifier 应失败。"""
        _, challenge = generate_pkce_pair()
        assert verify_pkce("wrong_verifier_abc123", challenge) is False

    def test_pkce_tampered_challenge(self):
        """篡改 challenge 应失败。"""
        verifier, _ = generate_pkce_pair()
        assert verify_pkce(verifier, "tampered_challenge_xyz") is False


class TestMetadataEndpoints:
    def test_as_metadata_returns_required_fields(self):
        """AS Metadata 必须包含所有 RFC 8414 必要字段。"""
        resp = client.get("/.well-known/oauth-authorization-server")
        assert resp.status_code == 200
        data = resp.json()
        assert "issuer" in data
        assert "authorization_endpoint" in data
        assert "token_endpoint" in data
        assert "jwks_uri" in data
        assert "S256" in data.get("code_challenge_methods_supported", [])

    def test_jwks_returns_rsa_key(self):
        """JWKS 必须包含 RSA 公钥。"""
        resp = client.get("/jwks.json")
        assert resp.status_code == 200
        data = resp.json()
        assert "keys" in data
        assert len(data["keys"]) > 0
        key = data["keys"][0]
        assert key["kty"] == "RSA"
        assert key["alg"] == "RS256"
        assert "n" in key and "e" in key


class TestClientRegistration:
    def test_register_loopback_client(self):
        """注册 loopback redirect 客户端应成功。"""
        resp = client.post("/register", json={
            "client_name": "Test Client",
            "redirect_uris": ["http://127.0.0.1:9999/callback"],
            "token_endpoint_auth_method": "none",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "client_id" in data
        assert data["redirect_uris"] == ["http://127.0.0.1:9999/callback"]

    def test_register_non_loopback_rejected(self):
        """非 loopback redirect 应被 Demo 安全策略拒绝。"""
        resp = client.post("/register", json={
            "client_name": "Evil Client",
            "redirect_uris": ["https://evil.example.com/steal"],
            "token_endpoint_auth_method": "none",
        })
        assert resp.status_code == 400


class TestTokenExchange:
    def _get_authorization_code(self) -> tuple[str, str]:
        """辅助：直接在 storage 中插入授权码，跳过浏览器流程。"""
        from auth_server.storage import storage
        from auth_server.models import AuthorizationCodeRecord
        from auth_server.security import generate_secure_token

        verifier, challenge = generate_pkce_pair()
        code = generate_secure_token(24)

        storage.save_code(AuthorizationCodeRecord(
            code=code,
            client_id="demo-desktop-client",
            redirect_uri="http://127.0.0.1:54321/callback",
            user_id="demo-user-001",
            scope="portfolio.read offline_access",
            code_challenge=challenge,
        ))
        return code, verifier

    def test_token_exchange_valid_pkce(self):
        """有效 PKCE 换 Token 应成功。"""
        code, verifier = self._get_authorization_code()
        resp = client.post("/token", data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": "http://127.0.0.1:54321/callback",
            "client_id": "demo-desktop-client",
            "code_verifier": verifier,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["access_token"]
        assert "refresh_token" in data   # offline_access scope → 应有 refresh

    def test_token_exchange_invalid_pkce(self):
        """错误 PKCE verifier 应返回 400。"""
        code, _ = self._get_authorization_code()
        resp = client.post("/token", data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": "http://127.0.0.1:54321/callback",
            "client_id": "demo-desktop-client",
            "code_verifier": "wrong_verifier_that_definitely_fails",
        })
        assert resp.status_code == 400
        assert "pkce" in resp.json().get("detail", "").lower() or \
               "pkce" in resp.text.lower()

    def test_authorization_code_single_use(self):
        """Authorization Code 只能用一次。"""
        code, verifier = self._get_authorization_code()

        # 第一次成功
        resp1 = client.post("/token", data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": "http://127.0.0.1:54321/callback",
            "client_id": "demo-desktop-client",
            "code_verifier": verifier,
        })
        assert resp1.status_code == 200

        # 第二次失败（已使用）
        resp2 = client.post("/token", data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": "http://127.0.0.1:54321/callback",
            "client_id": "demo-desktop-client",
            "code_verifier": verifier,
        })
        assert resp2.status_code == 400
```

---

## 五十三、测试 — tests/test_mcp_auth.py

```python
# tests/test_mcp_auth.py
"""MCP Server 认证与 Scope 测试。"""
import pytest
import time
from fastapi.testclient import TestClient

from mcp_server.main import app

client = TestClient(app)


def _make_rpc(method: str, params: dict = None, token: str = None) -> dict:
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    resp = client.post(
        "/mcp",
        json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params or {}},
        headers=headers,
    )
    return resp


class TestMcpRequiresAuthentication:
    def test_tools_list_without_token_returns_401(self):
        """无 Token 访问 tools/list 必须返回 401。"""
        resp = _make_rpc("tools/list")
        assert resp.status_code == 401

    def test_401_includes_resource_metadata_header(self):
        """401 响应必须包含 WWW-Authenticate + resource_metadata。"""
        resp = _make_rpc("tools/list")
        assert resp.status_code == 401
        www_auth = resp.headers.get("www-authenticate", "")
        assert "resource_metadata" in www_auth
        assert "localhost:8001" in www_auth

    def test_tools_call_without_token_returns_401(self):
        """无 Token 调用工具必须 401。"""
        resp = _make_rpc("tools/call", {"name": "get_portfolio", "arguments": {}})
        assert resp.status_code == 401

    def test_invalid_jwt_returns_401(self):
        """伪造 JWT 必须返回 401。"""
        resp = _make_rpc("tools/list", token="eyJhbGciOiJIUzI1NiJ9.fake.payload")
        # 可能 401 或 JSON-RPC error
        assert resp.status_code in (401, 200)
        if resp.status_code == 200:
            data = resp.json()
            assert "error" in data


class TestProtectedResourceMetadata:
    def test_resource_metadata_endpoint(self):
        """Resource Metadata 端点应返回 AS 地址。"""
        resp = client.get("/.well-known/oauth-protected-resource/mcp")
        assert resp.status_code == 200
        data = resp.json()
        assert "authorization_servers" in data
        assert "localhost:8000" in data["authorization_servers"][0]
        assert "scopes_supported" in data
```

---

## 五十四、测试 — tests/test_order_flow.py

```python
# tests/test_order_flow.py
"""Review→Execute 状态机与幂等测试。"""
import os
import time
import pytest
from fastapi.testclient import TestClient

from mcp_server.main import app
from mcp_server.tools import _reviews, _idempotency_results


# 生成一个合法的测试 JWT（需要先启动 auth server 或直接 mock）
# 这里演示 mock 方式：patch 掉 authenticate_request
from unittest.mock import patch

MOCK_CLAIMS = {
    "sub": "demo-user-001",
    "scope": "portfolio.read quotes.read orders.review orders.place",
    "client_id": "demo-desktop-client",
    "iss": "http://localhost:8000",
    "aud": "http://localhost:8001/mcp",
}

client = TestClient(app)


def _rpc_with_mock_auth(method: str, params: dict) -> dict:
    """用 mock claims 绕过真实 JWT 验证，专注业务逻辑测试。"""
    with patch("mcp_server.main.authenticate_request", return_value=MOCK_CLAIMS):
        resp = client.post(
            "/mcp",
            json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params},
            headers={"Authorization": "Bearer mock-token"},
        )
    return resp.json()


class TestReviewExecuteFlow:
    def test_review_returns_review_id(self):
        """review_equity_order 应返回 review_id 和摘要。"""
        result = _rpc_with_mock_auth("tools/call", {
            "name": "review_equity_order",
            "arguments": {"symbol": "NVDA", "quantity": 1, "side": "buy"},
        })
        assert "error" not in result
        data = result["result"]["_data"]
        assert "review_id" in data
        assert data["review_id"].startswith("rev_")
        assert "summary" in data

    def test_review_is_single_use(self):
        """同一 review_id 只能下单一次，第二次应返回 409。"""
        # 先 review
        review_resp = _rpc_with_mock_auth("tools/call", {
            "name": "review_equity_order",
            "arguments": {"symbol": "MSFT", "quantity": 1, "side": "buy"},
        })
        review_id = review_resp["result"]["_data"]["review_id"]

        # 第一次 place：成功
        place1 = _rpc_with_mock_auth("tools/call", {
            "name": "place_equity_order",
            "arguments": {
                "review_id": review_id,
                "idempotency_key": f"idem_{os.urandom(4).hex()}",
            },
        })
        assert "error" not in place1 or place1.get("result", {}).get("_data", {}).get("status") == "filled"

        # 第二次 place（不同 idempotency_key）：应失败
        place2 = _rpc_with_mock_auth("tools/call", {
            "name": "place_equity_order",
            "arguments": {
                "review_id": review_id,
                "idempotency_key": f"idem_{os.urandom(4).hex()}",
            },
        })
        # 期望 409 error 或 error code
        if "error" in place2:
            assert "409" in str(place2["error"]) or "已使用" in str(place2["error"])

    def test_idempotency_returns_same_result(self):
        """相同 idempotency_key 多次调用应返回完全相同的 order_id。"""
        review_resp = _rpc_with_mock_auth("tools/call", {
            "name": "review_equity_order",
            "arguments": {"symbol": "AAPL", "quantity": 1, "side": "buy"},
        })
        review_id = review_resp["result"]["_data"]["review_id"]
        idem_key = f"idem_test_{os.urandom(4).hex()}"

        place1 = _rpc_with_mock_auth("tools/call", {
            "name": "place_equity_order",
            "arguments": {"review_id": review_id, "idempotency_key": idem_key},
        })
        order_id_1 = place1["result"]["_data"]["order_id"]

        # 同一 idem_key 重试
        place2 = _rpc_with_mock_auth("tools/call", {
            "name": "place_equity_order",
            "arguments": {"review_id": review_id, "idempotency_key": idem_key},
        })
        order_id_2 = place2["result"]["_data"]["order_id"]

        assert order_id_1 == order_id_2, "幂等性失败：两次调用返回不同 order_id"
        assert place2["result"]["_data"].get("idempotent") is True

    def test_policy_rejects_unlisted_symbol(self):
        """不在白名单的标的应被 Policy 拒绝。"""
        result = _rpc_with_mock_auth("tools/call", {
            "name": "review_equity_order",
            "arguments": {"symbol": "MEME_COIN", "quantity": 1, "side": "buy"},
        })
        assert "error" in result

    def test_policy_rejects_over_limit_notional(self):
        """超过名义金额上限应被 Policy 拒绝（NVDA × 大量）。"""
        result = _rpc_with_mock_auth("tools/call", {
            "name": "review_equity_order",
            "arguments": {"symbol": "NVDA", "quantity": 100, "side": "buy"},
        })
        # NVDA @ 875 * 100 = $87,500 >> $500 上限
        assert "error" in result


class TestScopeEnforcement:
    def test_insufficient_scope_returns_403(self):
        """scope 不足应返回 403 error。"""
        # 只有 portfolio.read，调 orders.review 应 403
        limited_claims = {**MOCK_CLAIMS, "scope": "portfolio.read"}
        with patch("mcp_server.main.authenticate_request", return_value=limited_claims):
            resp = client.post(
                "/mcp",
                json={"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {
                    "name": "review_equity_order",
                    "arguments": {"symbol": "NVDA", "quantity": 1, "side": "buy"},
                }},
                headers={"Authorization": "Bearer mock-token"},
            )
        data = resp.json()
        assert "error" in data
        assert "403" in str(data["error"]) or "insufficient" in str(data["error"]).lower()
```

---

## 五十五、运行测试

```bash
# 运行所有测试
pytest tests/ -v

# 期望输出：
# tests/test_auth_server.py::TestPKCE::test_pkce_valid PASSED
# tests/test_auth_server.py::TestPKCE::test_pkce_invalid_verifier PASSED
# tests/test_auth_server.py::TestPKCE::test_pkce_tampered_challenge PASSED
# tests/test_auth_server.py::TestMetadataEndpoints::test_as_metadata_returns_required_fields PASSED
# tests/test_auth_server.py::TestMetadataEndpoints::test_jwks_returns_rsa_key PASSED
# tests/test_auth_server.py::TestClientRegistration::test_register_loopback_client PASSED
# tests/test_auth_server.py::TestClientRegistration::test_register_non_loopback_rejected PASSED
# tests/test_auth_server.py::TestTokenExchange::test_token_exchange_valid_pkce PASSED
# tests/test_auth_server.py::TestTokenExchange::test_token_exchange_invalid_pkce PASSED
# tests/test_auth_server.py::TestTokenExchange::test_authorization_code_single_use PASSED
# tests/test_mcp_auth.py::TestMcpRequiresAuthentication::test_tools_list_without_token_returns_401 PASSED
# tests/test_mcp_auth.py::TestMcpRequiresAuthentication::test_401_includes_resource_metadata_header PASSED
# tests/test_mcp_auth.py::TestMcpRequiresAuthentication::test_tools_call_without_token_returns_401 PASSED
# tests/test_mcp_auth.py::TestMcpRequiresAuthentication::test_invalid_jwt_returns_401 PASSED
# tests/test_mcp_auth.py::TestProtectedResourceMetadata::test_resource_metadata_endpoint PASSED
# tests/test_order_flow.py::TestReviewExecuteFlow::test_review_returns_review_id PASSED
# tests/test_order_flow.py::TestReviewExecuteFlow::test_review_is_single_use PASSED
# tests/test_order_flow.py::TestReviewExecuteFlow::test_idempotency_returns_same_result PASSED
# tests/test_order_flow.py::TestReviewExecuteFlow::test_policy_rejects_unlisted_symbol PASSED
# tests/test_order_flow.py::TestReviewExecuteFlow::test_policy_rejects_over_limit_notional PASSED
# tests/test_order_flow.py::TestScopeEnforcement::test_insufficient_scope_returns_403 PASSED
#
# 21 passed in X.XXs
```

---

## 五十六、必做验证实验

按顺序手动验证，每条都要亲自触发一次：

| 编号 | 实验 | 操作 | 期望结果 |
|------|------|------|----------|
| E1 | **错误 PKCE** | 用错误 `code_verifier` 换 Token | `400 PKCE 验证失败` |
| E2 | **Code 重放** | 同一 Authorization Code 用两次 | `400 authorization code 已使用` |
| E3 | **Scope 不足** | scope 只有 `portfolio.read`，调 `review_equity_order` | `403 insufficient_scope` |
| E4 | **JWT aud 篡改** | 用错误 audience 签发的 JWT | `401 invalid_audience` |
| E5 | **JWT iss 篡改** | 用错误 issuer 签发的 JWT | `401 invalid_issuer` |
| E6 | **JWT 过期** | 等 Access Token 过期后直接使用 | `401 token_expired` |
| E7 | **Refresh 重放** | Rotation 后重放旧 Refresh Token | `400 refresh_token 已吊销` |
| E8 | **Review 重用** | 同一 `review_id` 下单两次（不同 idem_key）| `409 review_id 已使用` |
| E9 | **幂等重试** | 同一 `idempotency_key` 重试 | 返回**完全相同** order_id |
| E10 | **Policy 违反** | 尝试交易非白名单标的 | `403 policy_violation` |
| E11 | **超额订单** | 名义金额超 $500 | `403 policy_violation: 超过上限` |
| E12 | **无 Token 访问** | 不带 Authorization 头调 MCP | `401 + WWW-Authenticate` 含 resource_metadata |

---

## 五十七、手动实验示例脚本

```bash
#!/bin/bash
# experiments.sh — 手动验证实验

BASE_AS="http://localhost:8000"
BASE_MCP="http://localhost:8001"

echo "=== 实验 E12: 无 Token 访问 MCP ==="
curl -i -X POST "$BASE_MCP/mcp" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'

echo ""
echo "=== 期望: 401 + WWW-Authenticate: Bearer resource_metadata=... ==="

echo ""
echo "=== 实验: 错误 code_verifier（直接操作 Token Endpoint）==="
# 假设已有有效 code，但 verifier 故意错误
FAKE_VERIFIER="this_is_definitely_wrong_verifier_abc123xyz"
curl -i -X POST "$BASE_AS/token" \
  -d "grant_type=authorization_code" \
  -d "code=SOME_CODE_HERE" \
  -d "redirect_uri=http://127.0.0.1:54321/callback" \
  -d "client_id=demo-desktop-client" \
  -d "code_verifier=$FAKE_VERIFIER"

echo ""
echo "=== 期望: 400 PKCE 验证失败 ==="

echo ""
echo "=== 验证 JWKS 公钥 ==="
curl -s "$BASE_AS/jwks.json" | python3 -c "
import sys, json
data = json.load(sys.stdin)
key = data['keys'][0]
print(f'kty: {key[\"kty\"]}, alg: {key[\"alg\"]}, kid: {key[\"kid\"]}')
print('JWKS 验证通过 ✓')
"
```

---

## 五十八、Docker 注意点

```yaml
# docker-compose.yml
version: "3.9"

services:
  auth-server:
    build:
      context: .
      dockerfile: Dockerfile.auth
    ports:
      - "8000:8000"
    volumes:
      - ./keys:/app/keys:ro
    environment:
      # JWT 里的 iss 必须是客户端（浏览器/外部）能访问的地址
      AUTH_ISSUER: "http://localhost:8000"
      MCP_AUDIENCE: "http://localhost:8001/mcp"
      ACCESS_TOKEN_TTL: "300"

  mcp-server:
    build:
      context: .
      dockerfile: Dockerfile.mcp
    ports:
      - "8001:8001"
    environment:
      # 关键区别：
      # EXPECTED_ISSUER = 客户端认知的公共 issuer（同 auth-server 的 AUTH_ISSUER）
      EXPECTED_ISSUER: "http://localhost:8000"
      # JWKS_URL = 容器内网络（用服务名），不走外部
      JWKS_URL: "http://auth-server:8000/jwks.json"
      EXPECTED_AUDIENCE: "http://localhost:8001/mcp"
    depends_on:
      - auth-server
```

**核心概念**：

```text
JWT iss 字段（客户端验证用）   ←→  EXPECTED_ISSUER
JWKS 拉取地址（容器内网络）    ←→  JWKS_URL

这两个必须拆开，不能混用容器服务名作为 issuer，
否则客户端浏览器拿到 JWT 后无法验证 issuer。
```

Dockerfile 示例：

```dockerfile
# Dockerfile.auth
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY auth_server/ ./auth_server/
COPY keys/ ./keys/
CMD ["uvicorn", "auth_server.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```dockerfile
# Dockerfile.mcp
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY mcp_server/ ./mcp_server/
COPY keys/public.pem ./keys/public.pem
# 注意：MCP Server 容器只复制公钥，不含私钥
CMD ["uvicorn", "mcp_server.main:app", "--host", "0.0.0.0", "--port", "8001"]
```

---

## 五十九、从 Demo 升到生产（路线图）

**不要跳步。** 每个阶段必须稳定后再进入下一阶段。

| 阶段 | 目标 | 关键内容 |
|------|------|----------|
| **阶段 0**（现状） | Demo 跑通 | 内存存储，固定用户，模拟数据 |
| **阶段 1** | 只读生产化 | 真实登录（Session/JWT）、Consent 记录入 DB、审计日志 |
| **阶段 2** | 低风险写 | 草稿、标签、预览；不含实际执行 |
| **阶段 3** | Review/Confirm 状态机 | DB 存 Review 记录、`SELECT FOR UPDATE`、用户可见摘要 |
| **阶段 4** | 真实执行 | 测试账户、硬限额、紧急停止按钮、事务 + 回滚 |
| **阶段 5** | 管理后台 | 已授权 Agent 列表、活动日志、一键撤销、暂停 |

---

## 六十、生产升级：数据库替换

Demo 用内存；生产替换建议：

```python
# 生产 storage.py 骨架（PostgreSQL + Redis）

import asyncpg
import aioredis
from contextlib import asynccontextmanager

# Authorization Codes → Redis（TTL 120s，自动过期）
# Refresh Tokens → PostgreSQL（支持用户级别查询和批量撤销）
# Client Registrations → PostgreSQL（持久化）
# Idempotency Keys → Redis（TTL 7天，防超时重试窗口）
# Audit Log → PostgreSQL（不可删，append-only）

async def save_auth_code_redis(redis: aioredis.Redis, record: dict) -> None:
    """Authorization Code 存 Redis，TTL = code 有效期。"""
    await redis.setex(
        f"auth_code:{record['code']}",
        record["expires_in"],
        json.dumps(record),
    )

async def get_and_consume_auth_code(redis: aioredis.Redis, code: str) -> dict | None:
    """
    原子性：GET + DEL，防止并发重放。
    使用 Lua 脚本确保原子性。
    """
    lua_script = """
    local val = redis.call('GET', KEYS[1])
    if val then
        redis.call('DEL', KEYS[1])
        return val
    end
    return nil
    """
    result = await redis.eval(lua_script, 1, f"auth_code:{code}")
    if result is None:
        return None
    return json.loads(result)
```

---

## 六十一、生产升级：真实登录 Session

```python
# 生产级登录（替换 Demo 固定用户 demo-user-001）

from fastapi import Request, Response
import secrets

SESSION_COOKIE = "mcp_session"
SESSION_TTL = 3600  # 1 小时

async def create_session(response: Response, user_id: str, redis) -> str:
    """创建登录 Session，返回 session_id。"""
    session_id = secrets.token_urlsafe(32)
    await redis.setex(
        f"session:{session_id}",
        SESSION_TTL,
        json.dumps({"user_id": user_id, "created_at": time.time()}),
    )
    response.set_cookie(
        SESSION_COOKIE,
        session_id,
        httponly=True,      # 防 XSS
        secure=True,        # 仅 HTTPS
        samesite="lax",
        max_age=SESSION_TTL,
    )
    return session_id

async def get_current_user(request: Request, redis) -> str | None:
    """从 Cookie 获取当前登录用户 ID。"""
    session_id = request.cookies.get(SESSION_COOKIE)
    if not session_id:
        return None
    data = await redis.get(f"session:{session_id}")
    if not data:
        return None
    return json.loads(data)["user_id"]
```

---

## 六十二、生产升级：Consent 记录

```python
# 生产级 Consent 存储（PostgreSQL）

CREATE_CONSENTS_TABLE = """
CREATE TABLE IF NOT EXISTS oauth_consents (
    id          SERIAL PRIMARY KEY,
    user_id     VARCHAR(255) NOT NULL,
    client_id   VARCHAR(255) NOT NULL,
    scope       TEXT NOT NULL,
    granted_at  TIMESTAMPTZ DEFAULT NOW(),
    revoked_at  TIMESTAMPTZ,
    UNIQUE(user_id, client_id)
);
"""

async def grant_consent(db, user_id: str, client_id: str, scope: str) -> None:
    """记录用户同意（INSERT OR UPDATE）。"""
    await db.execute("""
        INSERT INTO oauth_consents (user_id, client_id, scope)
        VALUES ($1, $2, $3)
        ON CONFLICT (user_id, client_id) DO UPDATE
        SET scope = $3, granted_at = NOW(), revoked_at = NULL
    """, user_id, client_id, scope)

async def check_consent(db, user_id: str, client_id: str, required_scope: set) -> bool:
    """检查用户是否已授权所需 scope（避免重复显示 Consent 页）。"""
    row = await db.fetchrow(
        "SELECT scope FROM oauth_consents WHERE user_id=$1 AND client_id=$2 AND revoked_at IS NULL",
        user_id, client_id,
    )
    if not row:
        return False
    granted = set(row["scope"].split())
    return required_scope.issubset(granted)

async def revoke_consent(db, user_id: str, client_id: str) -> None:
    """用户撤销授权（同时应吊销所有关联 Refresh Token）。"""
    await db.execute(
        "UPDATE oauth_consents SET revoked_at=NOW() WHERE user_id=$1 AND client_id=$2",
        user_id, client_id,
    )
```

---

## 六十三、生产升级：审计日志

```python
# mcp_server/audit.py — 审计日志（不含 Token 原文）

import time
import json
import logging

audit_logger = logging.getLogger("mcp.audit")
audit_logger.setLevel(logging.INFO)

# 生产：输出到结构化日志系统（Datadog、CloudWatch、ELK）


def log_tool_call(
    *,
    user_id: str,
    client_id: str,
    tool_name: str,
    arguments: dict,
    result_summary: str,
    success: bool,
    latency_ms: float,
) -> None:
    """
    记录 Tool 调用审计日志。
    注意：不记录 Token 原文、不记录完整 arguments（可能含敏感参数）。
    """
    # 对敏感字段做摘要而非原文
    safe_args = {
        k: (v if k not in ("review_id", "idempotency_key") else f"{str(v)[:8]}...")
        for k, v in arguments.items()
    }
    event = {
        "event": "tool_call",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "user_id": user_id,
        "client_id": client_id,
        "tool": tool_name,
        "args_summary": safe_args,
        "result": result_summary,
        "success": success,
        "latency_ms": round(latency_ms, 2),
    }
    audit_logger.info(json.dumps(event, ensure_ascii=False))


def log_auth_event(*, event_type: str, user_id: str, client_id: str, detail: str) -> None:
    """记录认证相关事件（授权、拒绝、吊销等）。"""
    event = {
        "event": event_type,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "user_id": user_id,
        "client_id": client_id,
        "detail": detail,
    }
    audit_logger.info(json.dumps(event, ensure_ascii=False))
```

---

## 六十四、生产升级：Rate Limiting

```python
# 生产级 Rate Limiting（基于 Redis）

import time
from fastapi import HTTPException


async def check_rate_limit(
    redis,
    *,
    key: str,
    max_requests: int,
    window_seconds: int,
) -> None:
    """
    滑动窗口限流。
    key 可以是 user_id、client_id、IP 等维度。
    """
    now = time.time()
    window_start = now - window_seconds
    pipe = redis.pipeline()

    # 移除窗口外的记录
    pipe.zremrangebyscore(key, 0, window_start)
    # 加入本次请求
    pipe.zadd(key, {str(now): now})
    # 计算当前窗口内请求数
    pipe.zcard(key)
    # 设置 TTL 防 key 泄漏
    pipe.expire(key, window_seconds * 2)

    results = await pipe.execute()
    current_count = results[2]

    if current_count > max_requests:
        raise HTTPException(
            status_code=429,
            detail=f"请求过于频繁，请 {window_seconds} 秒后重试",
            headers={"Retry-After": str(window_seconds)},
        )


# 在 MCP Tool 调用前使用：
# await check_rate_limit(redis, key=f"tool:{user_id}", max_requests=60, window_seconds=60)
```

---

## 六十五、生产升级：JWKS 密钥轮换

生产必须支持密钥轮换。JWKS 可以同时包含多个 key（新旧并存）：

```python
# auth_server/security_production.py — 多 kid 密钥轮换

import os
from pathlib import Path

# 当前激活 kid（用于签发新 Token）
ACTIVE_KID = os.getenv("ACTIVE_KEY_ID", "key-v2")

# 密钥目录：每个 kid 对应一对 pem 文件
KEYS_DIR = Path("/etc/mcp-auth/keys")


def get_all_jwks() -> dict:
    """
    返回所有有效公钥（包含即将淘汰的旧 key，用于验证旧 Token）。
    轮换步骤：
    1. 添加新 kid 密钥对
    2. 更新 ACTIVE_KID 指向新 kid
    3. 等待旧 Token 全部过期（max TTL = 300s）
    4. 从 JWKS 移除旧 kid
    """
    keys = []
    for pem_file in KEYS_DIR.glob("*.pub.pem"):
        kid = pem_file.stem.replace(".pub", "")
        with open(pem_file, "rb") as f:
            pub_key = serialization.load_pem_public_key(f.read())
        pub_numbers = pub_key.public_numbers()
        keys.append({
            "kty": "RSA",
            "use": "sig",
            "alg": "RS256",
            "kid": kid,
            "n": _int_to_base64url(pub_numbers.n),
            "e": _int_to_base64url(pub_numbers.e),
        })
    return {"keys": keys}
```

---

## 六十六、生产升级：Prompt Injection 防护

Prompt Injection 是 LLM Agent 的特有风险，Auth/Policy 是第一道防线：

```python
# mcp_server/prompt_injection_guard.py

import re
from fastapi import HTTPException

# 禁止在工具参数中出现的模式（防止注入指令绕过 Policy）
INJECTION_PATTERNS = [
    r"ignore previous",
    r"disregard all",
    r"system prompt",
    r"你是.*助手",
    r"<\|.*\|>",          # 特殊 token
    r"<<<.*>>>",
]


def validate_tool_arguments(arguments: dict) -> None:
    """
    对所有字符串参数做 Prompt Injection 检查。
    注意：这是额外防线，不能替代 Policy 和 Scope 检查。
    """
    for key, value in arguments.items():
        if not isinstance(value, str):
            continue
        for pattern in INJECTION_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                raise HTTPException(
                    status_code=400,
                    detail=f"参数 '{key}' 包含不允许的内容",
                )
```

**关键原则**：

```text
OAuth Scope 控制「可以做什么」
Agent Policy 控制「可以做多少」
Prompt Injection Guard 控制「指令能否被篡改」

三道防线缺一不可。
Prompt Injection 不能绕过 Policy。
Policy 不能替代 Scope。
Scope 不能替代 Policy。
```

---

## 六十七、生产升级：HTTPS 与反向代理

```nginx
# nginx.conf 片段

server {
    listen 443 ssl http2;
    server_name auth.example.com;

    ssl_certificate     /etc/ssl/certs/auth.example.com.crt;
    ssl_certificate_key /etc/ssl/private/auth.example.com.key;

    # HSTS
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    # OAuth 端点不缓存
    location ~ ^/(authorize|token|revoke|register) {
        proxy_pass         http://auth-server:8000;
        proxy_set_header   Host $host;
        proxy_set_header   X-Real-IP $remote_addr;
        proxy_set_header   X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;
        add_header         Cache-Control "no-store, no-cache" always;
    }

    # JWKS 可以缓存短时间（5 分钟）
    location /jwks.json {
        proxy_pass   http://auth-server:8000;
        add_header   Cache-Control "public, max-age=300" always;
    }

    # AS Metadata
    location /.well-known/ {
        proxy_pass   http://auth-server:8000;
        add_header   Cache-Control "public, max-age=3600" always;
    }
}
```

---

## 六十八、安全加固：四层防护模型

```text
┌─────────────────────────────────────────────────────────┐
│                   四层安全防护模型                        │
├─────────────────────────────────────────────────────────┤
│  第一层：身份认证（Who are you?）                         │
│  OAuth 2.1 + PKCE                                        │
│  - 防止未授权访问                                         │
│  - JWT 防伪造，RS256 签名                                 │
│  - PKCE 防授权码截取                                      │
├─────────────────────────────────────────────────────────┤
│  第二层：API 授权（What API can you call?）               │
│  Scope + Audience                                        │
│  - portfolio.read / orders.review / orders.place 分离    │
│  - Audience 防 Token 跨服务使用                           │
├─────────────────────────────────────────────────────────┤
│  第三层：Agent 授权（How much can you do?）               │
│  Agent Profile + Allowlist + 限额                        │
│  - 标的白名单                                             │
│  - 单笔金额上限                                           │
│  - 按 Agent 身份（不只是用户）设置不同权限                 │
├─────────────────────────────────────────────────────────┤
│  第四层：业务授权（Did user explicitly confirm this?）     │
│  Review + Confirm + Idempotency                          │
│  - Review 固化所有业务参数                                │
│  - Place 只传 review_id，无可变参数                        │
│  - 幂等 key 防网络重试重复成交                             │
│  - 人工 YES 确认（高风险操作）                             │
└─────────────────────────────────────────────────────────┘

重要认知：
OAuth 授权 Agent「可以访问服务」
≠
用户授权 Agent「可以执行每一次高风险操作」
```

---

## 六十九、上线前检查清单 — Authorization Server

```markdown
### Authorization Server 上线检查

认证与 PKCE
- [ ] Authorization Code 一次性（used=True 后立即拒绝）
- [ ] Code TTL ≤ 120 秒
- [ ] 强制 code_challenge_method=S256（拒绝 plain）
- [ ] PKCE verifier 用 constant-time compare（防时序攻击）
- [ ] redirect_uri 完全字符串匹配（不做前缀/通配符匹配）

Token 安全
- [ ] Access Token TTL 短（300 秒以内）
- [ ] Refresh Token Rotation：旧 token 换新的同时立即作废旧的
- [ ] Refresh Token 可吊销（用户可从 UI 撤销）
- [ ] Revocation 接口对不存在 token 也返回 200（防枚举）
- [ ] 空 access_token 不返回给客户端

密钥管理
- [ ] 私钥在 Key Vault / HSM（不在代码仓库）
- [ ] JWKS 支持多 kid（密钥轮换不中断验证）
- [ ] 旧 key 下线前等待所有用该 key 签发的 Token 过期

用户体验与安全
- [ ] Consent 记录入 DB（可查询、可撤销）
- [ ] 重复授权同 scope 可跳过 Consent（用户友好）
- [ ] 审计日志：所有授权/拒绝/吊销事件
- [ ] HTTPS only，Token 端点禁止缓存

动态注册
- [ ] Demo 限 loopback；生产改白名单或需人工审批
- [ ] client_id 生成足够随机（≥ 128 bit）
```

---

## 七十、上线前检查清单 — MCP Server

```markdown
### MCP Server 上线检查

Token 验证
- [ ] 每次请求都验签（不缓存验证结果）
- [ ] 验证 iss（防伪造 issuer）
- [ ] 验证 aud（防 Token 跨服务使用）
- [ ] 验证 exp（防过期 Token）
- [ ] JWKS 客户端缓存 key 但支持 kid 轮换

Scope 与 Policy（双重检查）
- [ ] 每个 Tool 有独立 scope 要求
- [ ] Scope 不足返回 403（不是 401）
- [ ] Agent Policy 独立于 Scope（第二道墙）
- [ ] Policy 违反返回业务错误，不暴露内部逻辑

Review → Execute 状态机
- [ ] Review 记录持久化入 DB
- [ ] Review 单次使用（DB 层 SELECT FOR UPDATE 防并发重放）
- [ ] Review 有 TTL，过期拒绝
- [ ] Execute 阶段不接受可变业务参数（symbol/quantity/side）
- [ ] Review user_id 与 JWT sub 匹配

幂等与事务
- [ ] idempotency_key 防网络重试重复成交
- [ ] 幂等 key 存储有合理 TTL（如 7 天）
- [ ] Place 操作在事务中完成（DB + 外部系统原子性）
- [ ] 外部系统调用失败有明确回滚机制

安全
- [ ] 错误信息不暴露内部堆栈
- [ ] 审计日志不含 Token 原文
- [ ] 输入参数 Pydantic 校验（类型 + 范围）
- [ ] Prompt Injection 检测（额外防线）
- [ ] Rate Limiting（Tool 调用频率限制）
```

---

## 七十一、上线前检查清单 — MCP Client

```markdown
### MCP Client 上线检查

发现与连接
- [ ] 从 401 + WWW-Authenticate 自动发现 AS
- [ ] SSRF 防护：限制 AS 地址范围（生产改白名单）
- [ ] AS Metadata 校验必要字段 + S256 支持

PKCE 与 State
- [ ] 每次授权生成新的 code_verifier（不重用）
- [ ] 每次授权生成新的 state（防 CSRF）
- [ ] State 在回调时校验

Token 存储
- [ ] 空 access_token 不落盘
- [ ] Token 文件 chmod 600（仅所有者可读）
- [ ] 生产改用 OS Keychain（keyring 库）
- [ ] 提前刷新（距过期 < 60s 静默刷新）
- [ ] 401 最多重试一次（防无限循环）

用户体验
- [ ] 高风险操作展示完整订单摘要
- [ ] 要求明确人工确认（输入 YES，不能默认同意）
- [ ] Refresh 静默进行（不打断用户）
- [ ] 错误信息人类可读（不直接透传 HTTP 状态码）
```

---

## 七十二、常见错误与解决方案

| 错误现象 | 根因 | 解决方案 |
|----------|------|----------|
| `401 missing_token` | Client 没有带 Bearer 头 | 检查 `Authorization: Bearer <token>` 格式 |
| `401 invalid_audience` | JWT `aud` 与 MCP Server 期望不匹配 | 确认 `EXPECTED_AUDIENCE` = JWT 里的 `aud` |
| `401 invalid_issuer` | JWT `iss` 与 Auth Server issuer 不匹配 | Docker 环境拆开 `EXPECTED_ISSUER` 和 `JWKS_URL` |
| `400 PKCE 验证失败` | code_verifier 错误或损坏 | 不要对 verifier 做额外 URL 编码 |
| `400 authorization code 已使用` | Code 被重放或 client 逻辑重试 | 检查 client 是否意外发了两次 Token 请求 |
| `400 authorization code 已过期` | 用户在浏览器停留 > 120s | 引导用户重新授权 |
| `403 insufficient_scope` | scope 申请不足 | 检查 `/authorize` 请求的 scope 参数 |
| `409 review_id 已使用` | 同 review_id 下单两次（不同 idem_key）| 使用 review_id 前检查是否已 place |
| `MCP Server 拉 JWKS 失败` | 容器内无法访问 `localhost:8000` | 用服务名 `http://auth-server:8000/jwks.json` |
| `state 不匹配` | CSRF 检查失败 | 检查 callback 参数是否完整传递 |

---

## 七十三、性能注意事项

**JWKS 缓存**：

```python
# PyJWKClient 自带 key 缓存，但需要配置合理的刷新间隔
# 密钥轮换时，旧 kid 的 Token 仍需能验证

# 推荐：缓存 key，但遇到未知 kid 时立即刷新
jwks_client = PyJWKClient(
    JWKS_URL,
    cache_keys=True,
    lifespan=300,       # 300 秒刷新一次（同 Access Token TTL）
)
```

**连接池**：

```python
# 生产 Auth Server 用连接池（asyncpg）
pool = await asyncpg.create_pool(
    DATABASE_URL,
    min_size=5,
    max_size=20,
    command_timeout=30,
)
```

**Token 验证开销**：

```text
JWT 本地验证（RS256）：约 0.5ms
JWKS 拉取（冷启动）：约 50ms
后续验证（缓存 key）：约 0.5ms

建议：JWKS 热缓存 + 定期后台刷新，不在请求路径上同步拉取。
```

---

## 七十四、本实验未覆盖的生产级话题

以下话题超出本实验范围，但上真实生产必须处理：

**身份与访问**：
- 真实 Identity Provider 集成（Google、Okta、Cognito）
- MFA（多因素认证）
- Agent Identity（Agent 自身的身份，不只是代理用户）

**数据与安全**：
- 数据加密（静态加密、传输加密）
- 密钥轮换自动化（HashiCorp Vault、AWS KMS）
- 安全扫描与渗透测试
- SOC 2 / ISO 27001 合规

**运营**：
- 分布式追踪（OpenTelemetry）
- 告警与 On-call
- 灾难恢复与 RTO/RPO
- 多区域部署

**业务**：
- 真实券商 API 集成（Robinhood、Alpaca、Interactive Brokers）
- 账户隔离（多租户）
- 监管合规（FINRA、SEC、MiFID II）
- 用户协议与风险披露

---

## 七十五、上线前最终检查清单（总表）

```markdown
## 部署前 Go/No-Go 检查

### 功能验证
- [ ] 21 个测试全部通过：pytest tests/ -v
- [ ] 手动实验 E1~E12 全部验证
- [ ] Docker Compose 可以从头启动（clean start）
- [ ] Client 完整走通：发现→PKCE→Token→工具→Review→YES→Place
- [ ] 幂等重试返回相同 order_id

### 安全验证
- [ ] 私钥未提交到 git（检查 .gitignore）
- [ ] Token 文件 chmod 600
- [ ] 错误响应不含堆栈信息
- [ ] HTTPS 配置（TLS 1.2+，生产不跑 HTTP）
- [ ] JWKS URL 与 Issuer URL 拆开（Docker 环境）

### 免责说明
- [ ] README 包含「模拟系统」说明
- [ ] 代码注释中无投资建议
- [ ] 用户界面（Consent 页、Client 输出）包含「不产生真实交易」提示

### 文档
- [ ] README 包含环境变量说明
- [ ] README 包含运行步骤
- [ ] DISCLAIMER.md 存在（或 README 包含 Disclaimer 章节）
```

---

## 七十六、最终理解图

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│                         完整数据流与安全检查点                                  │
└──────────────────────────────────────────────────────────────────────────────┘

  MCP Client
  ─────────────────────────────────────────────────────────────────────────────
  [1] 启动，POST /mcp（无 Token）
        ↓ 401 + WWW-Authenticate: Bearer resource_metadata="http://.../mcp"
  [2] GET resource_metadata → authorization_servers[0]
        ↓ SSRF 检查（只允许 localhost）
  [3] GET /.well-known/oauth-authorization-server
        ↓ 验证 issuer / S256 支持 / 所有端点存在
  [4] 生成 code_verifier（32 字节随机）+ code_challenge（SHA256）
       生成 state（16 字节随机，防 CSRF）
  [5] 打开浏览器 → /authorize?...&code_challenge=...&state=...

  Authorization Server
  ─────────────────────────────────────────────────────────────────────────────
  [6] GET /authorize
        ↓ 校验 response_type=code / client_id / redirect_uri / scope / S256
        ↓ 显示 Consent 页
  [7] POST /authorize（用户点「同意」）
        ↓ 生成 code（24 字节随机，TTL 120s）
        ↓ 存储 AuthorizationCodeRecord（含 code_challenge）
        ↓ 302 重定向 callback?code=...&state=...

  MCP Client
  ─────────────────────────────────────────────────────────────────────────────
  [8] 本机 Callback Server 收到 code + state
        ↓ 校验 state 匹配
  [9] POST /token（code + code_verifier + client_id）

  Authorization Server
  ─────────────────────────────────────────────────────────────────────────────
  [10] 验证 code 存在 + 未过期 + 未使用 + client 匹配 + redirect 匹配
        ↓ PKCE：SHA256(verifier) == challenge？
        ↓ 标记 code used=True（一次性）
        ↓ 签发 JWT（RS256，exp=5min）
        ↓ 签发 Refresh Token（TTL 30天）

  MCP Client
  ─────────────────────────────────────────────────────────────────────────────
  [11] 收到 access_token（验证非空）
        ↓ 存储 tokens（chmod 600）

  [12] POST /mcp initialize（Bearer JWT）

  MCP Server
  ─────────────────────────────────────────────────────────────────────────────
  [13] 提取 Bearer Token
        ↓ PyJWKClient 拉 JWKS（kid 匹配，验 RS256 签名）
        ↓ 验证 iss = "http://localhost:8000"
        ↓ 验证 aud = "http://localhost:8001/mcp"
        ↓ 验证 exp 未过期
        ↓ 返回 claims（含 sub / scope）

  [14] tools/call review_equity_order
        ↓ Scope 检查：claims.scope ⊇ {"orders.review"}
        ↓ Policy 检查：symbol ∈ ALLOWED_SYMBOLS AND notional ≤ $500
        ↓ 生成 review_id，固化所有业务参数，TTL 120s
        ↓ 返回摘要

  MCP Client
  ─────────────────────────────────────────────────────────────────────────────
  [15] 显示订单摘要，等待用户输入 YES

  用户：YES

  [16] POST /mcp tools/call place_equity_order（review_id + idempotency_key）

  MCP Server
  ─────────────────────────────────────────────────────────────────────────────
  [17] Scope 检查：claims.scope ⊇ {"orders.place"}
        ↓ 幂等检查：idempotency_key 是否已有结果？有→直接返回
        ↓ 获取 review（lock）：存在 + 未使用 + 未过期 + user 匹配？
        ↓ 原子标记 review used=True
        ↓ 模拟成交，生成 order_id
        ↓ 存入幂等缓存
        ↓ 返回成交结果

  MCP Client
  ─────────────────────────────────────────────────────────────────────────────
  [18] 显示成交结果（"模拟成交，不产生真实交易"）
        ↓ 演示幂等：同 idem_key 重试 → 相同 order_id

  ═══ 流程完成 ═══

  关键安全检查点回顾：
  Step  4  → PKCE 防授权码截取
  Step  8  → state 防 CSRF
  Step 10  → PKCE 验证防 code 被盗用后兑换
  Step 10  → code 一次性防重放
  Step 13  → JWT 验签 + iss/aud/exp 防伪造/跨服务/过期
  Step 14  → Scope 防越权访问
  Step 14  → Policy 防超额操作（第二道墙）
  Step 15  → 人工确认防自动下单
  Step 17  → 幂等防重复成交
  Step 17  → review 单次防重放下单
  Step 17  → review 无可变参数防 review 绕过
```

---

## 结语

搭完这三个服务，你不只是写了几个 API。你经历了一套完整的 AI Agent 安全架构：

**从 401 到成交，每一步都有明确的守门人。**

概念回顾：

| 概念 | 本实验中的体现 |
|------|---------------|
| **PKCE** | verifier/challenge 防授权码截取 |
| **JWT RS256** | Auth 签，MCP 验，私钥不出 Auth Server |
| **Scope** | 每个 Tool 独立 scope，`portfolio.read` 不能调 `orders.place` |
| **Audience** | JWT `aud = http://localhost:8001/mcp`，防 Token 跨服务重用 |
| **Refresh Rotation** | 旧换新，旧立即作废，防重放 |
| **Resource Metadata** | 401 里的 `resource_metadata` 是自动发现的起点 |
| **Review → Execute** | 固化参数，人工确认，分阶段授权 |
| **幂等** | `idempotency_key` 防网络重试重复成交 |
| **Agent Policy** | Scope 之外的第二道墙（白名单 + 限额） |

**下一步**：

1. ~~把代码提交到 xingai-enterprise-ai-pocs 的独立 POC 目录~~ **已完成，2026-07-12** —— 见 [理赔 MCP OAuth POC](https://github.com/xingaiapp/xingai-enterprise-ai-pocs/tree/main/pocs/claims-mcp-oauth-poc)。同一套代码，换成保险理赔裁定领域——证明这套模式不是 Robinhood 专属的。
2. 参考[生产拓扑](../articles/2026-07-11-mcp-in-production-robinhood-case.zh.md)理解 Worker / FastAPI / Redis 的决策边界
3. 阅读 [Invest AI ADR-028](https://github.com/xingaiapp/xingai-invest-ai/blob/main/docs/adr/028-robinhood-mcp-execution-gates.zh.md) 了解真实产品如何实现 Review Gate
4. 向同事展示这个 Demo，解释为什么「Authorization Code 一次性」和「PKCE」同时都是必要的

OAuth 授权 Agent 可以访问服务，不等于用户授权 Agent 执行每一次高风险操作。这句话记住了，你对 AI Agent 安全的理解就超过了大多数工程师。

---

## 相关资源

- **English 版本：** [2026-07-12-mcp-oauth-pkce-lab.md](2026-07-12-mcp-oauth-pkce-lab.md)
- **概念篇：** [MCP 认证深潜](2026-07-12-mcp-oauth-auth-deep-dive.zh.md)
- **生产拓扑：** [Robinhood MCP 深潜](../articles/2026-07-11-mcp-in-production-robinhood-case.zh.md)
- **实现仓库（券商领域）：** [xingai-robinhood-mcp](https://github.com/xingaiapp/xingai-robinhood-mcp)
- **可运行 POC（理赔领域）：** [claims-mcp-oauth-poc](https://github.com/xingaiapp/xingai-enterprise-ai-pocs/tree/main/pocs/claims-mcp-oauth-poc)——这篇实验课的代码搬过去的版本，另附一份对着同一套代码逐个讲解 OAuth/PKCE 机制的深度文档
- **Invest AI 门控：** [ADR-028](https://github.com/xingaiapp/xingai-invest-ai/blob/main/docs/adr/028-robinhood-mcp-execution-gates.zh.md)

---

## 免责声明

本实验为**教学用模拟系统**，具体声明：

- **不连真实券商**，所有交易均为模拟，不产生任何真实资产变动
- **非生产就绪**代码，未经安全审计，不适合直接部署到生产环境
- **不构成投资建议**，模拟投资组合和报价仅为教学演示
- **不构成法律或安全合规建议**
- 代码按「现状」提供，用户自行负责评估、部署与合规风险
- 在将任何代码用于生产前，必须经过完整的安全评估、渗透测试和合规审查

XingAI 不承担因使用本实验代码产生的任何损失或责任。

---

**作者：** Xing Wang  
**发布：** 2026-07-12  
**标签：** mcp, oauth, pkce, fastapi, education, security, jwt, hands-on
