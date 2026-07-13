---
title: 从 Robinhood MCP 看懂 MCP 认证 —— OAuth 2.1 / PKCE / Token 验证新手深潜
author: Xing Wang
date: 2026-07-12
tags: [mcp, oauth, pkce, jwt, security, education, agents, robinhood, human-in-the-loop]
description: 以 Robinhood Agentic Trading MCP 为教学案例，逐步拆解 MCP 认证：元数据发现、PKCE、Token 存储与刷新、JWT/Introspection、Scope、Review→Execute，以及新手常见坑。
---

# 从 Robinhood MCP 看懂 MCP 认证：带代码逐步拆解的新手教程

**English:** [English](2026-07-12-mcp-oauth-auth-deep-dive.md)  
**动手实验（下一篇）：** [从零搭建 OAuth 2.1 + PKCE MCP 项目](2026-07-12-mcp-oauth-pkce-lab.zh.md)  
**架构姊妹篇（生产拓扑）：** [生产环境里 MCP 如何真正运转](../articles/2026-07-11-mcp-in-production-robinhood-case.zh.md)  
**实现参考：** [xingai-robinhood-mcp](https://github.com/xingaiapp/xingai-robinhood-mcp)

---

## 写在前面

2026 年 5 月 27 日，Robinhood 宣布向 AI Agent 开放服务：用户可以把 Agent 接到 Robinhood，用于管理和自动化交易及信用卡消费，并附带安全控制与活动记录。

Agentic Trading 使用**独立 Agentic Account**。用户需先有正常个人投资账户，再在连接 Trading MCP 时完成 Agentic Account 开通与授权。认证与开通常要求在**桌面设备**完成。

一个能「帮你花钱」甚至「帮你下单」的服务，认证设计好坏直接决定它是安全工具还是潜在灾难。

本文以 **Robinhood 官方 MCP** 为教学案例，结合 **OAuth 2.1、PKCE、Protected Resource Metadata、Token Refresh、Scope、JWT 验证、高风险工具确认**，逐步讲清：

1. MCP Client 如何发现 Authorization Server  
2. 为什么桌面客户端不能保存 `client_secret`  
3. PKCE 防住了什么  
4. OAuth 回调服务器怎么工作  
5. Access Token 如何存储与刷新  
6. MCP Server 如何验证 Token  
7. 如何在自己的 MCP 项目里实现认证  
8. 如何防止 Agent 未经确认执行高风险操作  

文中 URL 与参数多为**示意**，用于解释概念。实际接入以服务返回的元数据和官方文档为准，不要硬编码本文示例值。

**不是投资建议。** 不鼓励把真实资金账户接到未审计的自建 MCP。XingAI 侧实现见 [xingai-robinhood-mcp](https://github.com/xingaiapp/xingai-robinhood-mcp)。

---

## 一、MCP 认证要解决什么问题

四个角色：

| 角色 | 作用 |
|------|------|
| Resource Owner | 用户，拥有账户和数据 |
| MCP Client | Claude、ChatGPT、Cursor 或自研 Agent |
| MCP Server / Resource Server | 提供 tools / resources / prompts |
| Authorization Server | 登录、授权、签发 Token |

交易场景里的信任链：

```text
用户 ──授权──▶ AI Agent / MCP Client
                    │ Bearer Access Token
                    ▼
              MCP Trading Server
                    │
                    ▼
                 券商账户
```

核心问题：

> Agent 如何证明得到了用户授权，同时又不需要接触用户账户密码？

---

## 二、反面教材：把密码塞进 MCP 配置

```json
{
  "mcpServers": {
    "robinhood": {
      "command": "uvx",
      "args": ["robinhood-mcp"],
      "env": {
        "ROBINHOOD_USERNAME": "your_email@example.com",
        "ROBINHOOD_PASSWORD": "your_password"
      }
    }
  }
}
```

这种做法的问题：

- 明文密码可被任何读到该配置文件的进程或人看到  
- Agent 拿到近乎完整的账户权限，没有细分只读 / 交易  
- 泄露后只能改总密码，其他所有 Agent 也跟着失效  
- 无法单独吊销某一个 Agent  
- 难以审计是哪个客户端做了哪些操作  

正确的形状：

```text
MCP 配置 → 只保存 MCP Server URL
用户登录 → 在服务商网页完成（浏览器弹出）
MCP Client → 只拿到有限权限、有限时间的 Token
```

---

## 三、OAuth 里的三种凭证

| 凭证 | 生命周期 | 用途 |
|------|----------|------|
| Authorization Code | 极短，通常一次性 | 换 Token |
| Access Token | 短（分钟～小时） | 调用 MCP Server |
| Refresh Token | 较长 | 换新 Access Token |

```text
Authorization Code ──一次性──▶ Access Token + Refresh Token
                                      │ Access 过期
                                      ▼
                                 新的 Access Token
```

**最常见误区：** 把 Authorization Code 当 Bearer Token 直接用。必须先调用 `exchange_code_for_tokens`，才能得到真正的 `access_token`。

---

## 四、发现认证信息：两层 Metadata

不要直接猜 `/.well-known/oauth-authorization-server`。标准路径是两层：

```text
第一层：Protected Resource Metadata
  → MCP Server 告诉你：谁给我签发 Token？

第二层：Authorization Server Metadata
  → Auth Server 告诉你：authorize / token / register / PKCE 方法
```

完整发现流程：

```text
1. MCP Client 不带 Token 请求 MCP 端点
2. MCP Server 返回 401 + WWW-Authenticate
3. Client 解析 resource_metadata URL
4. GET resource_metadata URL → 拿到 authorization_servers 列表
5. GET authorization_servers[0]/.well-known/oauth-authorization-server
6. 拿到 authorization_endpoint / token_endpoint / PKCE 方法
```

---

## 五、从 401 + WWW-Authenticate 发现 Metadata

不带 Token 请求 MCP，期望服务器返回 `401`，Header 示意：

```http
HTTP/1.1 401 Unauthorized
WWW-Authenticate: Bearer resource_metadata="https://agent.example.com/.well-known/oauth-protected-resource/mcp/trading"
```

Python 解析示例：

```python
import re
import httpx

def extract_resource_metadata_url(www_auth_header: str) -> str | None:
    """从 WWW-Authenticate 头提取 resource_metadata URL。"""
    match = re.search(r'resource_metadata="([^"]+)"', www_auth_header)
    return match.group(1) if match else None

async def probe_mcp_for_metadata(mcp_url: str) -> str | None:
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            mcp_url,
            json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
            # 不带 Authorization 头
        )
        if resp.status_code == 401:
            www_auth = resp.headers.get("WWW-Authenticate", "")
            return extract_resource_metadata_url(www_auth)
    return None
```

---

## 六、读取并校验 Protected Resource Metadata

```python
from urllib.parse import urlparse

ALLOWED_METADATA_HOSTS = {"agent.example.com", "api.example.com"}
BLOCKED_PREFIXES = ("10.", "172.16.", "192.168.", "169.254.", "127.", "::1", "fd")

def is_safe_url(url: str) -> bool:
    """防止 SSRF：拒绝私网、link-local、元数据服务地址。"""
    parsed = urlparse(url)
    if parsed.scheme != "https":
        return False  # 生产必须 HTTPS
    host = parsed.hostname or ""
    if host in ("localhost",):
        return False
    for prefix in BLOCKED_PREFIXES:
        if host.startswith(prefix):
            return False
    return True

async def fetch_resource_metadata(resource_metadata_url: str) -> dict:
    if not is_safe_url(resource_metadata_url):
        raise ValueError(f"不安全的 metadata URL: {resource_metadata_url}")
    async with httpx.AsyncClient() as client:
        resp = await client.get(resource_metadata_url)
        resp.raise_for_status()
        data = resp.json()
    # 基本字段校验
    assert "resource" in data, "缺少 resource 字段"
    assert "authorization_servers" in data and data["authorization_servers"], \
        "缺少 authorization_servers"
    return data
```

`resource_metadata` 示例返回（字段为示意）：

```json
{
  "resource": "https://agent.example.com/mcp/trading",
  "authorization_servers": ["https://auth.example.com"],
  "scopes_supported": [
    "quotes.read", "portfolio.read",
    "orders.review", "orders.place", "cash.transfer"
  ],
  "bearer_methods_supported": ["header"]
}
```

---

## 七、读取 Authorization Server Metadata

```python
async def fetch_as_metadata(issuer: str) -> dict:
    as_metadata_url = issuer.rstrip("/") + "/.well-known/oauth-authorization-server"
    if not is_safe_url(as_metadata_url):
        raise ValueError(f"不安全的 AS metadata URL: {as_metadata_url}")
    async with httpx.AsyncClient() as client:
        resp = await client.get(as_metadata_url)
        resp.raise_for_status()
        data = resp.json()
    # 必须校验的字段
    assert data.get("issuer") == issuer, \
        f"issuer 不匹配: {data.get('issuer')} != {issuer}"
    assert "authorization_endpoint" in data, "缺少 authorization_endpoint"
    assert "token_endpoint" in data, "缺少 token_endpoint"
    pkce_methods = data.get("code_challenge_methods_supported", [])
    assert "S256" in pkce_methods, "AS 不支持 PKCE S256"
    return data
```

`as_metadata` 示例返回（字段为示意）：

```json
{
  "issuer": "https://auth.example.com",
  "authorization_endpoint": "https://auth.example.com/oauth/authorize",
  "token_endpoint": "https://auth.example.com/oauth/token",
  "registration_endpoint": "https://auth.example.com/oauth/register",
  "jwks_uri": "https://auth.example.com/.well-known/jwks.json",
  "revocation_endpoint": "https://auth.example.com/oauth/revoke",
  "introspection_endpoint": "https://auth.example.com/oauth/introspect",
  "code_challenge_methods_supported": ["S256"],
  "grant_types_supported": ["authorization_code", "refresh_token"],
  "token_endpoint_auth_methods_supported": ["none", "client_secret_basic"]
}
```

---

## 八、PKCE：桌面客户端为什么不需要 Client Secret

Public Client（Claude Desktop、CLI、Cursor 插件）里嵌入的 `client_secret` ≈ 公开信息。任何人解包安装包或读到配置文件都能提取它。

**PKCE（RFC 7636）的思路：**

1. 每次授权前，在本地生成高熵随机字符串 `code_verifier`  
2. 计算 `code_challenge = BASE64URL(SHA256(code_verifier))`  
3. 发送授权请求时附上 `code_challenge`（挑战，公开传输没关系）  
4. 换 Token 时再提交原始的 `code_verifier`  
5. Auth Server 重算挑战并用**常量时间比较**（`secrets.compare_digest`）

攻击者截获了 `?code=abc` 但没有原始 verifier → Token Exchange 失败。

MCP 安全规范要求客户端实现 PKCE。

---

## 九、PKCE 代码实现

```python
import hashlib
import base64
import secrets
import string

def generate_pkce_pair() -> tuple[str, str]:
    """
    返回 (code_verifier, code_challenge)。
    verifier 使用 RFC 7636 推荐字符集，长度 64 字节（高熵）。
    """
    # RFC 7636 要求 verifier 长度 43-128，字符集 [A-Z a-z 0-9 - . _ ~]
    alphabet = string.ascii_letters + string.digits + "-._~"
    code_verifier = "".join(secrets.choice(alphabet) for _ in range(64))

    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    code_challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")

    return code_verifier, code_challenge


# 使用示例
verifier, challenge = generate_pkce_pair()
print(f"verifier : {verifier[:16]}...  (len={len(verifier)})")
print(f"challenge: {challenge}")
```

输出示意：

```text
verifier : XzK8mQbRtYpA3f...  (len=64)
challenge: k_7aB3cDe9fGhIjKlMnOpQrStUvWxYz0123456789ABCDE
```

---

## 十、生成授权 URL 并在浏览器打开

```python
import urllib.parse
import secrets
import webbrowser

def build_authorization_url(
    authorization_endpoint: str,
    client_id: str,
    redirect_uri: str,
    scopes: list[str],
    code_challenge: str,
) -> tuple[str, str]:
    """
    返回 (authorization_url, state)。
    state 用于防 CSRF，在回调时必须原样校验。
    """
    state = secrets.token_urlsafe(32)
    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": " ".join(scopes),
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }
    url = authorization_endpoint + "?" + urllib.parse.urlencode(params)
    return url, state


# 使用示例（以 as_metadata 里的 endpoint 为准，下同）
auth_url, state = build_authorization_url(
    authorization_endpoint="https://auth.example.com/oauth/authorize",
    client_id="my-mcp-client",
    redirect_uri="http://127.0.0.1:9877/callback",
    scopes=["portfolio.read", "orders.review"],
    code_challenge=challenge,
)
webbrowser.open(auth_url)
print(f"State 已保存，等待回调...")
```

---

## 十一、本地 Callback Server 接收 Authorization Code

```python
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

class CallbackHandler(BaseHTTPRequestHandler):
    """只处理一次回调，然后关闭服务器。"""

    result: dict | None = None  # 由 handle() 写入
    _expected_state: str = ""

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path != "/callback":
            self.send_response(404)
            self.end_headers()
            return

        params = parse_qs(parsed.query)
        code = (params.get("code") or [""])[0]
        returned_state = (params.get("state") or [""])[0]
        error = (params.get("error") or [""])[0]

        if error:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(f"授权失败: {error}".encode())
            CallbackHandler.result = {"error": error}
        elif not secrets.compare_digest(returned_state, self._expected_state):
            # 常量时间比较防 timing attack
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"State \xe6\x9c\xaa\xe5\x8c\xb9\xe9\x85\x8d\xef\xbc\x8c\xe5\x8f\xaf\xe8\x83\xbd\xe4\xb8\xba CSRF \xe6\x94\xbb\xe5\x87\xbb")
            CallbackHandler.result = {"error": "state_mismatch"}
        else:
            self.send_response(200)
            self.end_headers()
            self.wfile.write("授权成功，请返回终端。".encode("utf-8"))
            # 不把完整 code 打进日志
            CallbackHandler.result = {"code": code}

        # 关闭服务器（在另一个线程）
        threading.Thread(target=self.server.shutdown, daemon=True).start()

    def log_message(self, *args):
        pass  # 静默，避免 code 泄进默认日志


def wait_for_callback(port: int, state: str, timeout: int = 120) -> str:
    """启动临时 HTTP 服务器，等待回调，返回 code。"""
    CallbackHandler._expected_state = state
    CallbackHandler.result = None
    server = HTTPServer(("127.0.0.1", port), CallbackHandler)
    server.timeout = timeout
    server.handle_request()  # 阻塞直到收到一次请求或超时
    result = CallbackHandler.result or {}
    if "error" in result:
        raise RuntimeError(f"OAuth 回调错误: {result['error']}")
    code = result.get("code", "")
    if not code:
        raise RuntimeError("回调中没有收到 code")
    return code
```

---

## 十二、Code 换 Token：200 ≠ 成功

```python
async def exchange_code_for_tokens(
    token_endpoint: str,
    client_id: str,
    code: str,
    redirect_uri: str,
    code_verifier: str,
) -> dict:
    payload = {
        "grant_type": "authorization_code",
        "client_id": client_id,
        "code": code,
        "redirect_uri": redirect_uri,
        "code_verifier": code_verifier,
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            token_endpoint,
            data=payload,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        resp.raise_for_status()
        data = resp.json()

    # HTTP 200 不等于成功，必须逐字段校验
    if "error" in data:
        raise RuntimeError(f"Token exchange 失败: {data['error']} — {data.get('error_description', '')}")

    access_token = data.get("access_token", "")
    if not access_token:
        raise RuntimeError("access_token 为空——请勿持久化该结果")

    token_type = data.get("token_type", "").lower()
    if token_type != "bearer":
        raise RuntimeError(f"token_type 非预期: {token_type}")

    expires_in = data.get("expires_in", 0)
    if not isinstance(expires_in, int) or expires_in <= 0:
        raise RuntimeError(f"expires_in 不合理: {expires_in}")

    return data
```

2026 年 6 月社区曾报告过：空 `accessToken` 被持久化，客户端却表现得像登录成功。只调用 `raise_for_status()` 是不够的。

---

## 十三、Token 存储：优先系统 Keychain

**错误做法：** 明文 `tokens.json` 进 Git / 备份目录。

**更好的做法：** 使用系统 Keychain（`keyring`）或云端 Secret Manager。

```python
import json
import time
import keyring

SERVICE_NAME = "xingai-mcp-client"

def save_tokens(account: str, token_data: dict) -> None:
    """把 Token 存入系统 Keychain，绝不写进文件。"""
    # 把 expires_in 转成绝对时间戳，方便之后判断是否需要刷新
    token_data = token_data.copy()
    if "expires_in" in token_data and "expires_at" not in token_data:
        token_data["expires_at"] = time.time() + token_data["expires_in"]
    keyring.set_password(SERVICE_NAME, account, json.dumps(token_data))


def load_tokens(account: str) -> dict | None:
    raw = keyring.get_password(SERVICE_NAME, account)
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def delete_tokens(account: str) -> None:
    try:
        keyring.delete_password(SERVICE_NAME, account)
    except keyring.errors.PasswordDeleteError:
        pass  # 已经不存在，忽略
```

---

## 十四、Token 刷新逻辑

把 `expires_in` 转成绝对 `expires_at`，提前约 60 秒刷新，避免「发出时未过期、到达时已过期」。

```python
REFRESH_BUFFER_SECONDS = 60  # 提前 60 秒刷新

def is_token_expired(token_data: dict) -> bool:
    expires_at = token_data.get("expires_at", 0)
    return time.time() >= expires_at - REFRESH_BUFFER_SECONDS


async def refresh_access_token(
    token_endpoint: str,
    client_id: str,
    refresh_token: str,
) -> dict:
    payload = {
        "grant_type": "refresh_token",
        "client_id": client_id,
        "refresh_token": refresh_token,
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            token_endpoint,
            data=payload,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        resp.raise_for_status()
        data = resp.json()

    if "error" in data:
        raise RuntimeError(f"Refresh 失败: {data['error']}")

    new_access_token = data.get("access_token", "")
    if not new_access_token:
        raise RuntimeError("Refresh 响应里 access_token 为空")

    return data


def merge_refreshed_tokens(old_tokens: dict, new_data: dict) -> dict:
    """
    Refresh Token Rotation：若响应带新 refresh_token 则保存；
    否则保留旧的（不是所有 AS 每次都返回新 refresh_token）。
    """
    merged = old_tokens.copy()
    merged["access_token"] = new_data["access_token"]
    merged["expires_at"] = time.time() + new_data.get("expires_in", 3600)
    if "refresh_token" in new_data:
        merged["refresh_token"] = new_data["refresh_token"]
    return merged
```

---

## 十五、并发刷新锁：防止多个请求同时刷新

```python
import asyncio

_refresh_lock = asyncio.Lock()

async def get_valid_access_token(
    account: str,
    token_endpoint: str,
    client_id: str,
) -> str:
    """
    返回有效的 access_token。
    如果过期则刷新（加锁，防止并发触发多次 Rotation）。
    """
    async with _refresh_lock:
        tokens = load_tokens(account)
        if tokens is None:
            raise RuntimeError("未登录，请先完成 OAuth 授权")

        if not is_token_expired(tokens):
            return tokens["access_token"]

        refresh_token = tokens.get("refresh_token")
        if not refresh_token:
            delete_tokens(account)
            raise RuntimeError("Refresh Token 不存在，请重新授权")

        new_data = await refresh_access_token(token_endpoint, client_id, refresh_token)
        merged = merge_refreshed_tokens(tokens, new_data)
        save_tokens(account, merged)
        return merged["access_token"]
```

> 多实例（多进程）场景：用 Redis / DB 锁替换 `asyncio.Lock`，否则 Rotation 下旧 refresh token 被并行使用会集体 `invalid_grant`。

---

## 十六、调用 MCP：JSON-RPC 也要验错

MCP 基于 JSON-RPC 2.0。HTTP 200 仍可能携带 `"error"` 字段。

```python
async def call_mcp_tool(
    mcp_url: str,
    access_token: str,
    tool_name: str,
    arguments: dict,
    request_id: int = 1,
) -> dict:
    payload = {
        "jsonrpc": "2.0",
        "id": request_id,
        "method": "tools/call",
        "params": {"name": tool_name, "arguments": arguments},
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            mcp_url,
            json=payload,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
            timeout=30,
        )

    if resp.status_code == 401:
        raise TokenExpiredError("Access Token 已过期，请刷新")
    resp.raise_for_status()

    data = resp.json()
    assert data.get("jsonrpc") == "2.0", "不是合法的 JSON-RPC 响应"

    if "error" in data:
        err = data["error"]
        raise RuntimeError(
            f"MCP 工具错误 [{err.get('code')}]: {err.get('message')}"
        )

    if "result" not in data:
        raise RuntimeError("JSON-RPC 响应既无 result 也无 error")

    return data["result"]


class TokenExpiredError(Exception):
    pass
```

带 401 自动刷新一次的包装：

```python
async def call_mcp_tool_with_retry(
    mcp_url: str,
    account: str,
    token_endpoint: str,
    client_id: str,
    tool_name: str,
    arguments: dict,
) -> dict:
    """调用 MCP 工具，遇到 401 只刷新并重试一次。"""
    for attempt in range(2):
        access_token = await get_valid_access_token(account, token_endpoint, client_id)
        try:
            return await call_mcp_tool(mcp_url, access_token, tool_name, arguments)
        except TokenExpiredError:
            if attempt == 1:
                # 刷新后仍 401 → 清除 Token，要求重新授权
                delete_tokens(account)
                raise RuntimeError("重新授权后仍然 401，Token 已清除，请重新登录")
            # 第一次 401：强制过期，下次循环会刷新
            tokens = load_tokens(account) or {}
            tokens["expires_at"] = 0
            save_tokens(account, tokens)
```

> **禁止** `while 401: refresh` 死循环。只刷新一次，再次 401 就清 Token。

---

## 十七、Scope：登录成功 ≠ 全部权限

细粒度 Scope 优于一个粗粒度的 `trading`：

| Scope | 风险 |
|-------|------|
| `quotes.read` | 低 |
| `portfolio.read` | 中低 |
| `orders.review` | 中 |
| `orders.place` | 高 |
| `cash.transfer` | 极高 |

**Least Privilege 原则：**

- 能读不写  
- 能 review 不 place  
- 能操作组合不能转账  

客户端还应校验服务器返回的 `scope` 是否覆盖请求的集合：

```python
def verify_granted_scopes(requested: list[str], granted_scope_str: str) -> None:
    granted = set(granted_scope_str.split())
    missing = set(requested) - granted
    if missing:
        raise PermissionError(
            f"服务器未授予以下 Scope: {missing}。"
            "请检查应用注册配置或用户是否拒绝了部分权限。"
        )
```

---

## 十八、Resource / Audience 绑定（RFC 8707）

Token 必须绑定到具体的 MCP Resource。这样一个 `quotes.read` API 的 Token 就无法被拿来调用交易 API。

```python
# 授权请求时附加 resource 参数
params["resource"] = "https://agent.example.com/mcp/trading"
```

**MCP Server 必须验证 `aud`：**

```python
def verify_jwt_audience(payload: dict, expected_audience: str) -> None:
    aud = payload.get("aud")
    if isinstance(aud, str):
        aud = [aud]
    if expected_audience not in (aud or []):
        raise PermissionError(
            f"Token audience 不匹配: 期望 {expected_audience}，收到 {aud}"
        )
```

---

## 十九、MCP Server 如何验 Token：概述

验证流程：

```text
1. 解析 Authorization: Bearer <token>
   ↓ 缺失 → 401 + WWW-Authenticate
2. 判断 Token 类型（JWT 有 "." 分隔；Opaque 无）
   ↓ JWT → 本地验签
   ↓ Opaque → 调用 Introspection Endpoint
3. 校验 iss / aud / exp / nbf / 算法 / kid
4. 按工具要求检查 Scope
   ↓ 不足 → 403 insufficient_scope
5. 通过 → 执行工具
```

---

## 二十、JWT 验证实现

```python
import time
from typing import Any
import httpx
from jose import jwt, JWTError, ExpiredSignatureError
from jose.exceptions import JWKError

_jwks_cache: dict[str, Any] = {}
_jwks_fetched_at: float = 0
JWKS_CACHE_TTL = 3600  # 1 小时缓存


async def get_jwks(jwks_uri: str) -> dict:
    global _jwks_cache, _jwks_fetched_at
    if time.time() - _jwks_fetched_at < JWKS_CACHE_TTL and _jwks_cache:
        return _jwks_cache
    async with httpx.AsyncClient() as client:
        resp = await client.get(jwks_uri)
        resp.raise_for_status()
        _jwks_cache = resp.json()
        _jwks_fetched_at = time.time()
    return _jwks_cache


async def verify_jwt(
    token: str,
    jwks_uri: str,
    expected_issuer: str,
    expected_audience: str,
    allowed_algorithms: list[str] | None = None,
) -> dict:
    """
    验证 JWT 签名、issuer、audience、过期时间。
    返回解码后的 payload。
    注意：绝对不能设置 verify_signature=False。
    """
    if allowed_algorithms is None:
        allowed_algorithms = ["RS256", "ES256"]

    jwks = await get_jwks(jwks_uri)

    try:
        payload = jwt.decode(
            token,
            jwks,
            algorithms=allowed_algorithms,
            audience=expected_audience,
            issuer=expected_issuer,
            options={
                "verify_exp": True,
                "verify_nbf": True,
                "verify_iss": True,
                "verify_aud": True,
                "verify_signature": True,  # 永远不改成 False
            },
        )
    except ExpiredSignatureError:
        raise PermissionError("Token 已过期")
    except JWTError as e:
        raise PermissionError(f"JWT 验证失败: {e}")

    return payload
```

---

## 二十一、Opaque Token Introspection

如果收到的 Token 不是 JWT（没有 `.` 分隔），就要调用 Introspection Endpoint：

```python
async def introspect_token(
    introspection_endpoint: str,
    token: str,
    client_id: str,
    client_secret: str | None = None,
) -> dict:
    data = {"token": token, "client_id": client_id}
    auth = None
    if client_secret:
        auth = (client_id, client_secret)

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            introspection_endpoint,
            data=data,
            auth=auth,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        resp.raise_for_status()
        result = resp.json()

    if not result.get("active"):
        raise PermissionError("Token 无效或已过期（active != true）")

    # 校验 audience 和 issuer
    expected_aud = "https://agent.example.com/mcp/trading"
    aud = result.get("aud")
    if isinstance(aud, str):
        aud = [aud]
    if expected_aud not in (aud or []):
        raise PermissionError(f"Introspection audience 不匹配: {aud}")

    return result
```

---

## 二十二、Scope 执行：工具级别

MCP Server 里每个高风险工具在执行前都要检查 Scope：

```python
def require_scopes(token_scopes: str, *required: str) -> None:
    """
    token_scopes: Token payload 里的 scope 字符串（空格分隔）
    required: 工具需要的 scope 列表
    """
    granted = set(token_scopes.split())
    missing = [s for s in required if s not in granted]
    if missing:
        # 返回标准 OAuth 错误，Client 可据此提示重新授权
        raise PermissionError(
            f"insufficient_scope: 缺少 {missing}。"
            f"已授予: {granted}"
        )


# 工具层使用示例
async def tool_place_order(token_payload: dict, order_params: dict) -> dict:
    require_scopes(token_payload.get("scope", ""), "orders.place")
    # ... 下单逻辑
```

---

## 二十三、动态客户端注册

Auth Server 可提供 `registration_endpoint`。Public Client 常用 `token_endpoint_auth_method=none`，不依赖固定 `client_secret`。

```python
async def register_client(
    registration_endpoint: str,
    client_name: str,
    redirect_uris: list[str],
    scopes: list[str],
) -> dict:
    payload = {
        "client_name": client_name,
        "redirect_uris": redirect_uris,
        "grant_types": ["authorization_code", "refresh_token"],
        "response_types": ["code"],
        "scope": " ".join(scopes),
        "token_endpoint_auth_method": "none",  # Public Client
        "code_challenge_method": "S256",
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            registration_endpoint,
            json=payload,
            headers={"Content-Type": "application/json"},
        )
        resp.raise_for_status()
        data = resp.json()

    assert "client_id" in data, "注册响应缺少 client_id"
    return data
```

注册结果应与 `issuer` 绑定保存（不要把某个 AS 注册的 `client_id` 发给另一个 AS）：

```python
def save_client_registration(issuer: str, registration: dict) -> None:
    keyring.set_password(
        SERVICE_NAME,
        f"registration:{issuer}",
        json.dumps(registration),
    )
```

---

## 二十四、Review → Confirm → Execute

OAuth 只回答「用户是否授权了这个客户端」。它**不回答**「用户是否确认了这一笔交易」。

模型可能把「帮我看看 NVDA」理解成「立即买入」。高风险工具必须拆开：

```text
review_equity_order  → 只预览，不执行，返回 review_id + 摘要
用户确认摘要（明确看到 symbol / qty / 价格）
place_equity_order   → 只引用 review_id（不再传 symbol/qty）
```

```python
import uuid
import time

# 服务端内存 / 数据库存储（示意）
_pending_reviews: dict[str, dict] = {}
REVIEW_TTL_SECONDS = 120  # Review 最多 2 分钟内有效


def create_review(
    user_id: str,
    symbol: str,
    side: str,
    quantity: float,
    order_type: str,
    limit_price: float | None = None,
) -> dict:
    """
    创建 Review 记录，冻结参数。
    返回展示给用户的摘要和 review_id。
    """
    review_id = str(uuid.uuid4())
    review = {
        "review_id": review_id,
        "user_id": user_id,
        "symbol": symbol,
        "side": side,
        "quantity": quantity,
        "order_type": order_type,
        "limit_price": limit_price,
        "created_at": time.time(),
        "used": False,
    }
    _pending_reviews[review_id] = review
    summary = (
        f"您即将 {'买入' if side == 'buy' else '卖出'} "
        f"{quantity} 股 {symbol}，"
        f"类型: {order_type}"
        + (f"，限价: ${limit_price:.2f}" if limit_price else "")
    )
    return {"review_id": review_id, "summary": summary}


def execute_from_review(review_id: str, user_id: str, idempotency_key: str) -> dict:
    """
    用 review_id 执行下单。
    参数完全从 Review 记录读取，不允许外部修改。
    """
    review = _pending_reviews.get(review_id)
    if not review:
        raise ValueError(f"Review {review_id} 不存在")
    if review["user_id"] != user_id:
        raise PermissionError("Review 与用户不匹配")
    if review["used"]:
        raise ValueError("Review 已被使用，不能重复执行")
    if time.time() - review["created_at"] > REVIEW_TTL_SECONDS:
        raise ValueError("Review 已过期，请重新 review")

    review["used"] = True  # 单次使用

    # 实际提交到券商（此处示意）
    order_result = {
        "status": "submitted",
        "review_id": review_id,
        "idempotency_key": idempotency_key,
        "symbol": review["symbol"],
        "side": review["side"],
        "quantity": review["quantity"],
    }
    return order_result
```

---

## 二十五、Idempotency-Key 防网络重试重复下单

```python
import hashlib

# 服务端已处理集合（生产用数据库存储 + TTL）
_processed_idempotency_keys: set[str] = set()


def generate_idempotency_key(review_id: str, user_id: str) -> str:
    """基于 review_id + user_id 生成确定性 Idempotency-Key。"""
    raw = f"{user_id}:{review_id}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def check_and_mark_idempotency(key: str) -> bool:
    """
    返回 True 表示首次处理；False 表示重复请求（直接返回缓存结果）。
    """
    if key in _processed_idempotency_keys:
        return False
    _processed_idempotency_keys.add(key)
    return True
```

Review → Execute 流程加上 Idempotency：

```text
Client: review_equity_order(symbol, qty)
Server: 返回 review_id + summary
Client 展示给用户
用户确认
Client: place_equity_order(review_id, idempotency_key)
Server: 验证 review → 执行下单 → 标记 key 已使用
网络重试: 同一 key → 返回已缓存的结果，不重复下单
```

与 XingAI [ADR-028](https://github.com/xingaiapp/xingai-invest-ai/blob/main/docs/adr/028-robinhood-mcp-execution-gates.zh.md) 门控、以及 [xingai-robinhood-mcp](https://github.com/xingaiapp/xingai-robinhood-mcp) gateway 的 fail-closed 思路一致：**提示词不是门禁，代码才是。**

---

## 二十六、不要把用户 Token 原样转发给下游

```text
危险做法：
MCP Client → Access Token → MCP Server → 直接转发同一 Token → 第三方 API

问题：
- Audience 错误（Token 是给 MCP Server 的，不是给第三方的）
- 下游可以拿到本不该有的 Token
- 审计边界模糊（谁调用了第三方？以谁的身份？）
```

正确做法：

```text
方案 A（Service Credential）：
MCP Server 验证用户 Token → 确认 scope 足够 → 用 Server 自己的 credential 调内部 / 券商 API

方案 B（Token Exchange，RFC 8693）：
MCP Server 调 token_exchange_endpoint，以用户 Token 换一个 audience=第三方 API 的新 Token
```

```python
async def exchange_token_for_downstream(
    token_exchange_endpoint: str,
    subject_token: str,
    audience: str,
    client_id: str,
) -> str:
    """RFC 8693 Token Exchange，换取 audience 为下游服务的新 Token。"""
    payload = {
        "grant_type": "urn:ietf:params:oauth:grant-type:token-exchange",
        "client_id": client_id,
        "subject_token": subject_token,
        "subject_token_type": "urn:ietf:params:oauth:token-type:access_token",
        "audience": audience,
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            token_exchange_endpoint,
            data=payload,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        resp.raise_for_status()
        data = resp.json()
    return data["access_token"]
```

---

## 二十七、Token 吊销与登出

```python
async def revoke_token(
    revocation_endpoint: str,
    token: str,
    token_type_hint: str,  # "access_token" 或 "refresh_token"
    client_id: str,
) -> None:
    payload = {
        "token": token,
        "token_type_hint": token_type_hint,
        "client_id": client_id,
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            revocation_endpoint,
            data=payload,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        # RFC 7009：即使 token 不存在也应返回 200
        if resp.status_code not in (200, 400):
            resp.raise_for_status()


async def logout(
    account: str,
    revocation_endpoint: str,
    client_id: str,
) -> None:
    """完整登出流程：先吊销，再删本地存储。"""
    tokens = load_tokens(account)
    if tokens:
        # 先吊销 refresh token（吊销后 access token 也会失效）
        rt = tokens.get("refresh_token")
        if rt:
            await revoke_token(revocation_endpoint, rt, "refresh_token", client_id)
        at = tokens.get("access_token")
        if at:
            await revoke_token(revocation_endpoint, at, "access_token", client_id)
    delete_tokens(account)
```

---

## 二十八、日志安全：绝不记录凭证

```python
import logging
import re

SENSITIVE_PATTERNS = [
    (re.compile(r'(?i)(access_token|refresh_token|code_verifier|code|password)\s*[=:]\s*\S+'), r'\1=***REDACTED***'),
    (re.compile(r'Bearer\s+[A-Za-z0-9\-._~+/]+=*'), 'Bearer ***REDACTED***'),
    (re.compile(r'(?i)"(access_token|refresh_token)"\s*:\s*"[^"]+"'), r'"\1": "***REDACTED***"'),
]


class RedactingFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        msg = str(record.getMessage())
        for pattern, replacement in SENSITIVE_PATTERNS:
            msg = pattern.sub(replacement, msg)
        record.msg = msg
        record.args = ()
        return True


logger = logging.getLogger("mcp_client")
logger.addFilter(RedactingFilter())
```

---

## 二十九、审计记录

审计要记录「发生了什么」，而不是凭证本身：

```python
import datetime

def audit_log(
    user_id: str,
    client_id: str,
    tool_name: str,
    decision: str,          # "allowed" / "denied" / "pending_review"
    review_id: str | None,
    result: str | None,
    scope_used: str | None = None,
) -> None:
    """
    写入审计记录。生产里写入不可变日志（数据库 / SIEM）。
    绝对不包含 access_token / refresh_token / code。
    """
    entry = {
        "ts": datetime.datetime.utcnow().isoformat() + "Z",
        "user_id": user_id,
        "client_id": client_id,
        "tool": tool_name,
        "decision": decision,
        "review_id": review_id,
        "result": result,
        "scope_used": scope_used,
    }
    # 此处简化为打印；生产写入数据库或 SIEM
    logger.info("AUDIT %s", entry)
```

---

## 三十、发布 Protected Resource Metadata

MCP Server 自己也要发布 Metadata，让 Client 能发现它。

```python
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.applications import Starlette

PROTECTED_RESOURCE_METADATA = {
    "resource": "https://agent.example.com/mcp/trading",
    "authorization_servers": ["https://auth.example.com"],
    "scopes_supported": [
        "quotes.read",
        "portfolio.read",
        "orders.review",
        "orders.place",
    ],
    "bearer_methods_supported": ["header"],
    "resource_documentation": "https://docs.example.com/mcp/trading",
}


async def protected_resource_metadata(request):
    return JSONResponse(PROTECTED_RESOURCE_METADATA)


async def mcp_endpoint(request):
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        metadata_url = (
            "https://agent.example.com"
            "/.well-known/oauth-protected-resource/mcp/trading"
        )
        return JSONResponse(
            {"error": "unauthorized"},
            status_code=401,
            headers={
                "WWW-Authenticate": f'Bearer resource_metadata="{metadata_url}"'
            },
        )
    # ... 正常处理
    return JSONResponse({"jsonrpc": "2.0", "id": 1, "result": {}})


app = Starlette(routes=[
    Route(
        "/.well-known/oauth-protected-resource/mcp/trading",
        protected_resource_metadata,
    ),
    Route("/mcp/trading", mcp_endpoint, methods=["POST"]),
])
```

---

## 三十一、Robinhood 案例里的纵深防御

公开信息表明 Agentic Trading 用**独立 Agentic Account**，而不是让 Agent 无限制操作主账户：

1. **账户隔离** — 风险边界更清晰，爆炸半径有限  
2. **权限隔离** — 交易 / 银行 / 信用卡不应共享无限 Token  
3. **活动可见** — 谁、何时、哪个客户端、是否确认、结果如何  
4. **可撤销** — 在服务商侧吊销，而不只靠 Agent「退出登录」  

不管你在做什么 MCP，这四个原则都值得复制：

```text
独立账户 / 独立 Credential  →  限制爆炸半径
细粒度 Scope                →  最小权限
可见活动日志                →  事后审计
服务商级吊销                →  即时失效
```

---

## 三十二、新手最常见的十个错误

| 错误 | 后果 | 正确做法 |
|------|------|----------|
| 密码放进 MCP 配置 | 账户暴露 | OAuth |
| 桌面保存 Client Secret | 可被提取 | Public Client + PKCE |
| 不校验 State | CSRF | 随机 State + 常量时间比较 |
| 直接猜 Token Endpoint | 易被误导 | Metadata Discovery |
| HTTP 200 就当成功 | 空 Token 入库 | 校验字段 |
| Token 写进日志 | 凭证泄露 | Redaction |
| Access Token 长期保存 | 泄露窗口大 | 短期 + Refresh |
| 401 无限重试 | 死循环 | 只刷新一次 |
| Review 后仍可改参数 | 绕过确认 | Review ID 固化参数 |
| 不验 Audience | 跨服务滥用 | 验 `aud` |

---

## 小结

**生产级检查清单（摘要）**

**Client 侧：**

- [ ] 从 Resource Metadata + AS Metadata 发现端点（不要硬编码）  
- [ ] PKCE S256，每次授权生成新 verifier  
- [ ] State 防 CSRF，常量时间比较  
- [ ] Redirect URI 严格匹配  
- [ ] Token Exchange 后校验非空、类型、expires_in  
- [ ] Token 存 Keychain，绝不写明文文件  
- [ ] `expires_at` = `now + expires_in`，提前 60 秒刷新  
- [ ] 并发刷新加锁  
- [ ] 401 只刷新一次，再次 401 清 Token  
- [ ] Logout 先 Revocation 后删本地  
- [ ] 日志 Redaction  

**Server 侧：**

- [ ] 无 Token → 401 + `WWW-Authenticate` 指向 Resource Metadata  
- [ ] JWT → JWKS 验签，检查 `iss` / `aud` / `exp` / `nbf` / 算法 / kid  
- [ ] Opaque Token → Introspection，要求 `active: true`  
- [ ] 工具级 Scope 检查，不足 → 403 `insufficient_scope`  
- [ ] 不接受 query string 里的 Token  
- [ ] 不随意透传用户 Token 给下游  
- [ ] 高风险工具 Rate Limit  
- [ ] 发布自己的 Protected Resource Metadata  
- [ ] 完整审计记录（不含凭证）  

**高风险工具：**

- [ ] 独立隔离账户  
- [ ] Review → Execute，Review 短期过期且单次使用  
- [ ] Execute 参数从 Review 记录读取，不允许外部修改  
- [ ] Idempotency-Key 防重复下单  
- [ ] 单日 / 单笔限额  
- [ ] 显式确认（用户看到 symbol / qty / 价格）  
- [ ] 可暂停 / 可吊销  

完整动手勾选清单见 [动手实验篇](2026-07-12-mcp-oauth-pkce-lab.zh.md) 末尾。

---

浓缩成一张图：

```text
标准发现 → OAuth 2.1 → PKCE → 短期 Access Token
    → 最小 Scope → Resource/Audience 绑定
    → 独立 Agent 账户 → Review + 用户确认
    → 限额 / 幂等 / 审计 → 随时吊销
```

一句话：

> 密码不交给 Agent；Token 不拥有无限权限；高风险操作不能只靠一次登录；任何执行都必须可限制、可确认、可审计、可撤销。

评估新 MCP 时先问：

1. 为什么要我的密码，而不是浏览器 OAuth？  
2. Token 的 Audience 和 Scope 是什么？  
3. Token 泄露后攻击者最多能做什么？  
4. 高风险工具是否需要单独确认？  
5. 能否在服务商侧立即吊销这个 Agent？  

答不清，就不要让它碰真钱、生产数据或核心系统。

---

## 下一步

动手搭一套可运行的 Auth Server + MCP Server + Client（模拟投资组合，**不接真实券商**）：

→ [从零搭建 OAuth 2.1 + PKCE MCP 项目](2026-07-12-mcp-oauth-pkce-lab.zh.md)

看同一套模式搬出券商领域、用在保险理赔裁定上的可运行 POC，用理赔权限策略层代替名义金额上限：

→ [理赔 MCP OAuth POC](https://github.com/xingaiapp/xingai-enterprise-ai-pocs/tree/main/pocs/claims-mcp-oauth-poc)——自带一份 `docs/mcp-auth-deep-dive.zh.md`，把这篇文章的每个概念都对应到真实的理赔领域代码上

生产拓扑与 gateway fail-closed：

→ [生产环境里 MCP 如何真正运转](../articles/2026-07-11-mcp-in-production-robinhood-case.zh.md)

---

## 免责声明

本文代码用于教学与架构演示。省略了分布式锁、数据库事务、HSM、完整 SSRF 防御、DPoP、Token Exchange 完整实现、云端 Secret Manager、合规审计系统、以及适用于生产的错误处理与监控等细节。

Robinhood 的实际端点、工具名、Scope、Token 格式和认证流程可能随产品变化。实际集成以 MCP 元数据、官方说明和当前客户端实现为准。本文示例 URL（如 `agent.example.com`、`auth.example.com`）均为教学示意，不代表任何实际服务地址。

内容仅供信息与教育目的，按「现状」提供，不构成投资、法律或安全合规建议。用户自行负责评估与使用风险。不鼓励将真实资金账户连接到未经充分安全审计的自建 MCP 系统。

动手实验（不使用真实券商，仅模拟数据）继续见姊妹篇：[从零搭建 OAuth 2.1 + PKCE MCP 项目](2026-07-12-mcp-oauth-pkce-lab.zh.md)。

---

**作者：** Xing Wang  
**发布：** 2026-07-12  
**标签：** mcp, oauth, pkce, jwt, security, education
