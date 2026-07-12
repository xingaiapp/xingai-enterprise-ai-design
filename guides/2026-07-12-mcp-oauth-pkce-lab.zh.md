---
title: 从零搭建 OAuth 2.1 + PKCE MCP 项目 —— 完整可运行实战
author: Xing Wang
date: 2026-07-12
tags: [mcp, oauth, pkce, fastapi, education, security, jwt, hands-on]
description: 动手搭建 Authorization Server + MCP Server + Python Client：元数据发现、PKCE、JWT、Scope、Review→Execute、幂等与测试。模拟投资组合，不接真实券商。
---

# 从零搭建 OAuth 2.1 + PKCE MCP 项目：完整可运行实战

**English:** [English](2026-07-12-mcp-oauth-pkce-lab.md)  
**概念篇（先读）：** [从 Robinhood MCP 看懂 MCP 认证](2026-07-12-mcp-oauth-auth-deep-dive.zh.md)

本实验把概念篇落成**三个可运行服务**。重点是认证与门禁，业务是**模拟**投资组合与下单 —— **不连接真实券商**。

---

## 1. 最终架构

```text
MCP Client ──OAuth──▶ Authorization Server (:8000)
     │                      │ JWT Access Token
     │                      ▼
     └──── Bearer ────▶ MCP Server (:8001)
                              │ Scope + Policy
                              ▼
                         模拟 Portfolio / Review / Place
```

| 服务 | 端口 | 职责 |
|------|------|------|
| Auth Server | 8000 | `/authorize`、`/token`、`/.well-known/...`、`/jwks.json`、`/revoke` |
| MCP Server | 8001 | 验 Token、`tools/list`、`tools/call`、Review→Execute |
| Client | CLI | 发现元数据、PKCE、存 Token、调工具 |

---

## 2. 目录结构

```text
secure-mcp-demo/
├── auth_server/          # main.py, models.py, security.py, storage.py
├── mcp_server/           # main.py, auth.py, tools.py, policies.py
├── client/               # main.py, oauth.py, discovery.py, token_store.py
├── tests/                # test_auth_server.py, test_mcp_auth.py, test_order_flow.py
├── keys/                 # private.pem, public.pem
├── requirements.txt
├── docker-compose.yml    # 可选
└── README.md
```

可把可运行代码落在 [xingai-enterprise-ai-pocs](https://github.com/xingaiapp/xingai-enterprise-ai-pocs) 的独立 POC 目录；本文给出**工业标准步骤与关键实现要点**，便于照着搭。

---

## 3. 环境

```bash
python -m venv .venv && source .venv/bin/activate
pip install fastapi uvicorn[standard] requests httpx \
  "PyJWT[crypto]" cryptography python-multipart pydantic keyring pytest
```

生成 RSA 密钥（Auth 持有私钥，MCP **只**需要公钥）：

```bash
mkdir -p keys
openssl genrsa -out keys/private.pem 2048
openssl rsa -in keys/private.pem -pubout -out keys/public.pem
```

---

## 4. Authorization Server（逐步）

### 4.1 数据模型

内存即可做 demo（生产改 PostgreSQL / Redis）：

- `AuthorizationCodeRecord`：code、client_id、redirect_uri、user_id、scope、code_challenge、expires_at、used  
- `RefreshTokenRecord`：token、client_id、user_id、scope、revoked、expires_at  
- `ClientRegistration`：client_id、redirect_uris、`token_endpoint_auth_method=none`

预置桌面客户端：`demo-desktop-client`，redirect `http://127.0.0.1:54321/callback`。

### 4.2 安全函数

- `verify_pkce(verifier, challenge)` — SHA256 + `compare_digest`  
- `create_access_token(...)` — RS256 JWT，声明含 `iss`、`sub`、`aud`、`scope`、`client_id`、`exp`（示例 300 秒）  
- `public_key_to_jwk()` — 暴露给 `/jwks.json`

示例 issuer：`http://localhost:8000`  
默认 audience：`http://localhost:8001/mcp`

### 4.3 必开端点

| 路径 | 作用 |
|------|------|
| `GET /.well-known/oauth-authorization-server` | AS Metadata |
| `GET /jwks.json` | 公钥 |
| `POST /register` | 动态注册（demo 可只允许 `127.0.0.1` redirect） |
| `GET/POST /authorize` | Consent 页 + 发 Authorization Code（~120s） |
| `POST /token` | `authorization_code` + `refresh_token`（Rotation：旧 refresh 立即作废） |
| `POST /revoke` | 吊销 refresh（不存在也常返回成功） |

Authorization 页 demo 可固定用户 `demo-user-001`。强制：`response_type=code`、`code_challenge_method=S256`、redirect 已注册、scope ⊆ 支持集合。

### 4.4 Token Exchange 检查清单

换 code 时拒绝：未知 code、已用、过期、client_id / redirect_uri 不匹配、**PKCE 失败**。  
成功后：`used=true`，返回 access + refresh + `expires_in` + `scope`。

### 4.5 启动

```bash
uvicorn auth_server.main:app --port 8000 --reload
curl http://localhost:8000/.well-known/oauth-authorization-server
curl http://localhost:8000/jwks.json
```

---

## 5. MCP Server（逐步）

### 5.1 `auth.py`

- 无 Bearer → **401** + `WWW-Authenticate: Bearer resource_metadata="http://localhost:8001/.well-known/oauth-protected-resource/mcp"`  
- `PyJWKClient` 拉 JWKS，验 `iss` / `aud` / `exp`  
- `require_scopes(claims, {"orders.place"})` → 不足则 **403**

### 5.2 `policies.py`（第二道墙）

即使有 `orders.place`：

- 标的白名单（如 NVDA、MSFT…）  
- 单笔上限（如 $500）  

OAuth Scope ≠ Agent Policy。

### 5.3 Tools

| Tool | Scope | 行为 |
|------|-------|------|
| `get_portfolio` | `portfolio.read` | 读模拟仓位 |
| `get_quote` | `quotes.read` | 模拟报价 |
| `review_equity_order` | `orders.review` | 生成 review_id，120s 过期，不执行 |
| `place_equity_order` | `orders.place` | 仅 `review_id` + `idempotency_key`；标记 used；幂等返回同一结果 |

**禁止**在 place 阶段再传可改的 symbol/quantity。

### 5.4 JSON-RPC `/mcp`

实现 `initialize`、`tools/list`、`tools/call`。工具内 `HTTPException` 转成 JSON-RPC error（带 status_code），不要把堆栈甩给客户端。

### 5.5 Protected Resource Metadata

```http
GET /.well-known/oauth-protected-resource/mcp
```

返回 `resource`、`authorization_servers: ["http://localhost:8000"]`、`scopes_supported`。

### 5.6 启动

```bash
uvicorn mcp_server.main:app --port 8001 --reload
curl -i -X POST http://localhost:8001/mcp \
  -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'
# 期望 401 + WWW-Authenticate
```

---

## 6. Client（逐步）

### 6.1 Discovery

1. POST MCP（无 Token）→ 解析 `resource_metadata`  
2. GET Resource Metadata → `authorization_servers[0]`  
3. GET AS Metadata → 校验 issuer、端点、S256  
4. Demo 限制 hostname 为 localhost / 127.0.0.1

### 6.2 OAuth

生成 PKCE + state → 打开浏览器 → 本机 Callback → 校验 state → code + verifier 换 Token → 校验非空 access_token → 写 `expires_at`。

Demo 可用权限收紧的本地文件（`chmod 600`）；生产改 Keychain。

### 6.3 调用

`initialize` → `tools/list` → `get_portfolio` → `review_equity_order` → 终端输入 **`YES`** → `place_equity_order`。

Token 将过期时刷新；收到 401 再刷新并重试**一次**。

### 6.4 运行

三个终端：

```bash
# T1
uvicorn auth_server.main:app --port 8000 --reload
# T2
uvicorn mcp_server.main:app --port 8001 --reload
# T3
python -m client.main
```

预期路径：401 → 发现 → PKCE → Consent → Token → tools → Review → 人工 YES → 模拟成交。

---

## 7. 必做验证实验

| 实验 | 期望 |
|------|------|
| 错误 `code_verifier` 换 Token | `invalid_grant` / PKCE failed |
| 同一 Authorization Code 用两次 | already used |
| Scope 只有 `portfolio.read` 调 review | 403 insufficient_scope |
| JWT `aud` 改成别的 API | 401 invalid audience |
| Refresh 后重放旧 refresh | revoked / invalid_grant |
| 同一 review 下单两次 | 409 already used |
| 同一 idempotency_key 重试 | 返回同一 order 结果 |

```bash
pytest -v
```

建议用例：`test_pkce_valid/invalid`、`test_mcp_requires_authentication`、`test_review_is_single_use`、`test_idempotency_returns_same_result`。

---

## 8. Docker 注意点

容器内 MCP 拉 JWKS 应用服务名（如 `http://auth-server:8000/jwks.json`），但 JWT 里的 **`iss` 必须是客户端认知的公共 Issuer**（如 `http://localhost:8000` 或生产 HTTPS）。用环境变量拆开：

```text
EXPECTED_ISSUER=https://auth.example.com
JWKS_URL=http://auth-server:8000/jwks.json
```

---

## 9. 从 Demo 升到生产（路线图）

| 阶段 | 内容 |
|------|------|
| 1 只读 | 认证 + JWT + Scope + 审计稳定后再谈写 |
| 2 低风险写 | 草稿 / 标签 / 预览 |
| 3 Review/Confirm | 状态机 + 用户可见摘要 |
| 4 真实执行 | 测试账户、限额、紧急停止、幂等、事务、回滚 |
| 5 管理后台 | 已授权 Agent、活动、撤销、暂停 |

补齐：真登录 Session、Consent 表、Agent Profile、Rate Limit、审计日志、密钥轮换（JWKS 多 kid）、HTTPS 与反向代理、SSRF 防护、Pydantic 校验 tool 参数、**Prompt Injection 不能绕过 Policy**、DB `SELECT … FOR UPDATE` 执行 Review。

四层安全模型：

```text
1 身份：OAuth 2.1 + PKCE
2 API 授权：Scope + Audience
3 Agent 授权：Profile + Allowlist + 限额
4 业务授权：Review + Confirm + Idempotency
```

> OAuth 授权 Agent 可以访问服务，不等于用户授权 Agent 执行每一次高风险操作。

---

## 10. 上线前检查清单

### Authorization Server

- [ ] Code 一次性、短寿命  
- [ ] 强制 PKCE S256  
- [ ] Redirect 完全匹配  
- [ ] Refresh Rotation + Revocation  
- [ ] 私钥在 Key Vault / HSM  
- [ ] JWKS 支持轮换  
- [ ] Consent 可查可撤  

### MCP Server

- [ ] 验签 + iss/aud/exp + Scope  
- [ ] Agent / Tool / 账户 / 金额策略  
- [ ] Review 单次 + Execute 无可变业务参数  
- [ ] Idempotency + 事务  
- [ ] 审计、无 Token 日志、错误不泄内部细节  

### MCP Client

- [ ] Metadata 发现 + SSRF 防护  
- [ ] 新 PKCE / 新 State  
- [ ] 空 Token 不落盘  
- [ ] 安全存储 + 提前刷新 + 锁  
- [ ] 401 只重试一次  
- [ ] 高风险操作展示完整摘要并显式确认  

---

## 相关

- 概念篇：[MCP 认证深潜](2026-07-12-mcp-oauth-auth-deep-dive.zh.md)  
- 生产拓扑：[Robinhood MCP 深潜](../articles/2026-07-11-mcp-in-production-robinhood-case.zh.md)  
- 实现仓库：[xingai-robinhood-mcp](https://github.com/xingaiapp/xingai-robinhood-mcp)  
- 门控：[Invest AI ADR-028](https://github.com/xingaiapp/xingai-invest-ai/blob/main/docs/adr/028-robinhood-mcp-execution-gates.zh.md)

---

## 免责声明

本实验为教学用模拟系统，非生产就绪，不构成投资、法律或安全合规建议。代码按「现状」提供。用户自行负责评估、部署与合规。

---

**作者：** Xing Wang  
**发布：** 2026-07-12  
**标签：** mcp, oauth, pkce, fastapi, education
