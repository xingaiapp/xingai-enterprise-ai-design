---
title: MCP Auth Deep Dive — OAuth 2.1, PKCE, and Token Verification for Beginners (Robinhood Case)
author: Xing Wang
date: 2026-07-12
tags: [mcp, oauth, pkce, jwt, security, education, agents, robinhood, human-in-the-loop]
description: A step-by-step education guide to MCP authentication using Robinhood Agentic Trading MCP as the teaching case — metadata discovery, PKCE, token storage and refresh, JWT verification, scopes, review-before-execute, and ten common beginner mistakes. Every concept includes working Python code.
---

# MCP Auth from Robinhood: OAuth 2.1 / PKCE / Token Verification — Beginner Deep Dive

**中文版：** [中文](2026-07-12-mcp-oauth-auth-deep-dive.zh.md)  
**Hands-on lab (next):** [Build an OAuth 2.1 + PKCE MCP project from scratch](2026-07-12-mcp-oauth-pkce-lab.md)  
**Architecture sibling (production topology):** [How MCP Works in Production](../articles/2026-07-11-mcp-in-production-robinhood-case.md)  
**Implementation reference:** [xingai-robinhood-mcp](https://github.com/xingaiapp/xingai-robinhood-mcp)

---

## Why This Guide Exists

On 27 May 2026 Robinhood announced Agentic access: users can connect an AI agent to Robinhood to manage and automate trades and credit card spending, with security controls and activity logs built in.

Agentic Trading runs on a **separate Agentic Account**. You need a healthy personal brokerage account first, then complete Agentic Account setup when you connect the Trading MCP. Auth and onboarding typically require a **desktop device**.

If a service can spend your money or place orders on your behalf, the auth design determines whether it is a useful tool or a disaster waiting to happen.

This guide uses **Robinhood's official MCP** as the teaching case. It works through each piece of the stack:

1. How an MCP client discovers the Authorization Server  
2. Why desktop clients must not embed a `client_secret`  
3. What PKCE actually blocks  
4. How a loopback callback server works  
5. How to store and refresh access tokens  
6. How an MCP server verifies tokens  
7. How to implement auth in your own MCP project  
8. How to stop agents from running high-risk tools without explicit confirmation  

URLs and parameters throughout are **illustrative**. They explain concepts. For real integrations always follow live metadata and official vendor docs — never hard-code example values from this article.

**Not investment advice.** Do not wire real money to an unaudited home-built MCP. XingAI implementation notes live in [xingai-robinhood-mcp](https://github.com/xingaiapp/xingai-robinhood-mcp).

---

## 1. What MCP Auth Must Solve

Four roles:

| Role | Job |
|------|-----|
| Resource Owner | The user who owns the account and data |
| MCP Client | Claude, ChatGPT, Cursor, or your own agent host |
| MCP Server / Resource Server | Serves tools, resources, and prompts |
| Authorization Server | Handles login, consent, and token issuance |

The trust chain in a trading scenario:

```text
User ──authorizes──▶ AI Agent / MCP Client
                          │ Bearer Access Token
                          ▼
                    MCP Trading Server
                          │
                          ▼
                      Brokerage Account
```

Core question:

> How does the agent prove the user authorized it — without ever touching the user's account password?

---

## 2. Anti-Pattern: Passwords in MCP Config

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

Problems with this approach:

- Any process or person who reads the config file sees the password in plain text  
- The agent gets near-full account power with no read-only / trading split  
- A leak forces a full password change, breaking every other connected agent at once  
- You cannot revoke a single agent independently  
- No audit trail — you cannot tell which client did what  

Correct shape:

```text
MCP config → stores only the MCP Server URL
User login → happens on the vendor's browser page (browser popup)
MCP Client → receives only a short-lived, limited-scope token
```

---

## 3. Three Different Credentials

| Credential | Lifetime | Purpose |
|------------|----------|---------|
| Authorization Code | Seconds; usually one-shot | Exchange for tokens |
| Access Token | Minutes to hours | Call the MCP server |
| Refresh Token | Longer | Get a new access token |

```text
Authorization Code ──one-shot──▶ Access Token + Refresh Token
                                       │ Access expires
                                       ▼
                                  New Access Token
```

**Most common misconception:** sending the Authorization Code as a Bearer token directly. You must call `exchange_code_for_tokens` first to get the real `access_token`.

---

## 4. Discovery Is Two Layers

Do not guess `/.well-known/oauth-authorization-server`. The standard path is two steps:

```text
Layer 1: Protected Resource Metadata
  → The MCP Server tells you: "Who issues tokens for me?"

Layer 2: Authorization Server Metadata
  → The Auth Server tells you: authorize / token / register / PKCE methods
```

Full discovery flow:

```text
1. MCP Client calls the MCP endpoint with no token
2. MCP Server returns 401 + WWW-Authenticate
3. Client parses the resource_metadata URL from the header
4. GET resource_metadata URL → receives the authorization_servers list
5. GET authorization_servers[0]/.well-known/oauth-authorization-server
6. Receives authorization_endpoint / token_endpoint / PKCE methods
```

---

## 5. Finding Metadata from 401 + WWW-Authenticate

Call the MCP endpoint with no token. Expect the server to return `401` with a header like:

```http
HTTP/1.1 401 Unauthorized
WWW-Authenticate: Bearer resource_metadata="https://agent.example.com/.well-known/oauth-protected-resource/mcp/trading"
```

Python to extract and follow it:

```python
import re
import httpx

def extract_resource_metadata_url(www_auth_header: str) -> str | None:
    """Extract the resource_metadata URL from a WWW-Authenticate header."""
    match = re.search(r'resource_metadata="([^"]+)"', www_auth_header)
    return match.group(1) if match else None

async def probe_mcp_for_metadata(mcp_url: str) -> str | None:
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            mcp_url,
            json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
            # No Authorization header
        )
        if resp.status_code == 401:
            www_auth = resp.headers.get("WWW-Authenticate", "")
            return extract_resource_metadata_url(www_auth)
    return None
```

---

## 6. Fetching and Validating Protected Resource Metadata

```python
from urllib.parse import urlparse

ALLOWED_METADATA_HOSTS = {"agent.example.com", "api.example.com"}
BLOCKED_PREFIXES = ("10.", "172.16.", "192.168.", "169.254.", "127.", "::1", "fd")

def is_safe_url(url: str) -> bool:
    """Block SSRF: reject private networks, link-local, and metadata service addresses."""
    parsed = urlparse(url)
    if parsed.scheme != "https":
        return False  # Production must use HTTPS
    host = parsed.hostname or ""
    if host in ("localhost",):
        return False
    for prefix in BLOCKED_PREFIXES:
        if host.startswith(prefix):
            return False
    return True

async def fetch_resource_metadata(resource_metadata_url: str) -> dict:
    if not is_safe_url(resource_metadata_url):
        raise ValueError(f"Unsafe metadata URL: {resource_metadata_url}")
    async with httpx.AsyncClient() as client:
        resp = await client.get(resource_metadata_url)
        resp.raise_for_status()
        data = resp.json()
    # Basic field validation
    assert "resource" in data, "Missing 'resource' field"
    assert "authorization_servers" in data and data["authorization_servers"], \
        "Missing or empty 'authorization_servers'"
    return data
```

Example `resource_metadata` response (fields are illustrative):

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

## 7. Fetching Authorization Server Metadata

```python
async def fetch_as_metadata(issuer: str) -> dict:
    as_metadata_url = issuer.rstrip("/") + "/.well-known/oauth-authorization-server"
    if not is_safe_url(as_metadata_url):
        raise ValueError(f"Unsafe AS metadata URL: {as_metadata_url}")
    async with httpx.AsyncClient() as client:
        resp = await client.get(as_metadata_url)
        resp.raise_for_status()
        data = resp.json()
    # Required field checks
    assert data.get("issuer") == issuer, \
        f"Issuer mismatch: {data.get('issuer')} != {issuer}"
    assert "authorization_endpoint" in data, "Missing authorization_endpoint"
    assert "token_endpoint" in data, "Missing token_endpoint"
    pkce_methods = data.get("code_challenge_methods_supported", [])
    assert "S256" in pkce_methods, "AS does not support PKCE S256"
    return data
```

Example `as_metadata` response (fields are illustrative):

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

## 8. PKCE: Why Desktop Clients Don't Need a Client Secret

A `client_secret` baked into a desktop install (Claude Desktop, CLI, Cursor plugin) is effectively public. Anyone who decompiles the package or reads the config file can extract it.

**PKCE (RFC 7636) works differently:**

1. Before each authorization, generate a high-entropy random string: `code_verifier`  
2. Compute `code_challenge = BASE64URL(SHA256(code_verifier))`  
3. Send `code_challenge` with the authorization request (fine to transmit — it is a hash)  
4. Send the original `code_verifier` when exchanging the code for tokens  
5. The Auth Server recomputes the challenge and compares with **constant-time comparison** (`secrets.compare_digest`)  

An attacker who intercepts `?code=abc` but does not have the original verifier cannot complete the token exchange.

MCP security guidance requires clients to implement PKCE.

---

## 9. PKCE Code Implementation

```python
import hashlib
import base64
import secrets
import string

def generate_pkce_pair() -> tuple[str, str]:
    """
    Returns (code_verifier, code_challenge).
    Verifier uses the RFC 7636 recommended character set, 64 bytes (high entropy).
    """
    # RFC 7636 requires verifier length 43-128, charset [A-Z a-z 0-9 - . _ ~]
    alphabet = string.ascii_letters + string.digits + "-._~"
    code_verifier = "".join(secrets.choice(alphabet) for _ in range(64))

    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    code_challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")

    return code_verifier, code_challenge


# Usage example
verifier, challenge = generate_pkce_pair()
print(f"verifier : {verifier[:16]}...  (len={len(verifier)})")
print(f"challenge: {challenge}")
```

Output (illustrative):

```text
verifier : XzK8mQbRtYpA3f...  (len=64)
challenge: k_7aB3cDe9fGhIjKlMnOpQrStUvWxYz0123456789ABCDE
```

---

## 10. Building the Authorization URL and Opening the Browser

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
    Returns (authorization_url, state).
    State is used for CSRF protection and must be compared exactly on callback.
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


# Usage (always use the endpoint from as_metadata, not a hard-coded value)
auth_url, state = build_authorization_url(
    authorization_endpoint="https://auth.example.com/oauth/authorize",
    client_id="my-mcp-client",
    redirect_uri="http://127.0.0.1:9877/callback",
    scopes=["portfolio.read", "orders.review"],
    code_challenge=challenge,
)
webbrowser.open(auth_url)
print(f"State saved — waiting for callback...")
```

---

## 11. Local Callback Server Receiving the Authorization Code

```python
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

class CallbackHandler(BaseHTTPRequestHandler):
    """Handles one callback request, then shuts down the server."""

    result: dict | None = None  # Written by handle()
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
            self.wfile.write(f"Authorization failed: {error}".encode())
            CallbackHandler.result = {"error": error}
        elif not secrets.compare_digest(returned_state, self._expected_state):
            # Constant-time comparison prevents timing attacks
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"State mismatch \xe2\x80\x94 possible CSRF attack")
            CallbackHandler.result = {"error": "state_mismatch"}
        else:
            self.send_response(200)
            self.end_headers()
            self.wfile.write("Authorization successful. Return to your terminal.".encode("utf-8"))
            # Do not log the raw code
            CallbackHandler.result = {"code": code}

        # Shut down the server on a separate thread
        threading.Thread(target=self.server.shutdown, daemon=True).start()

    def log_message(self, *args):
        pass  # Silent — avoids the code leaking into default HTTP server logs


def wait_for_callback(port: int, state: str, timeout: int = 120) -> str:
    """Start a temporary HTTP server, wait for callback, return the code."""
    CallbackHandler._expected_state = state
    CallbackHandler.result = None
    server = HTTPServer(("127.0.0.1", port), CallbackHandler)
    server.timeout = timeout
    server.handle_request()  # Blocks until one request arrives or timeout
    result = CallbackHandler.result or {}
    if "error" in result:
        raise RuntimeError(f"OAuth callback error: {result['error']}")
    code = result.get("code", "")
    if not code:
        raise RuntimeError("No code received in callback")
    return code
```

---

## 12. Code Exchange: HTTP 200 Is Not Enough

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

    # HTTP 200 does not mean success — validate every field
    if "error" in data:
        raise RuntimeError(f"Token exchange failed: {data['error']} — {data.get('error_description', '')}")

    access_token = data.get("access_token", "")
    if not access_token:
        raise RuntimeError("access_token is empty — do not persist this result")

    token_type = data.get("token_type", "").lower()
    if token_type != "bearer":
        raise RuntimeError(f"Unexpected token_type: {token_type}")

    expires_in = data.get("expires_in", 0)
    if not isinstance(expires_in, int) or expires_in <= 0:
        raise RuntimeError(f"Unreasonable expires_in: {expires_in}")

    return data
```

In mid-2026, community reports showed empty `accessToken` values being persisted while the UI displayed a "logged in" state. Calling `raise_for_status()` alone is not enough.

---

## 13. Token Storage: Prefer the System Keychain

**Wrong:** plaintext `tokens.json` committed to git or sitting in a backup directory.

**Better:** system keychain (`keyring`) or a cloud secret manager.

```python
import json
import time
import keyring

SERVICE_NAME = "xingai-mcp-client"

def save_tokens(account: str, token_data: dict) -> None:
    """Store tokens in the system keychain. Never write to a file."""
    # Convert expires_in to an absolute timestamp for later expiry checks
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
        pass  # Already gone — ignore
```

---

## 14. Token Refresh Logic

Convert `expires_in` to an absolute `expires_at` and refresh roughly 60 seconds early. This avoids the race where a token is valid when you send the request but expired by the time the server receives it.

```python
REFRESH_BUFFER_SECONDS = 60  # Refresh 60 seconds before actual expiry

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
        raise RuntimeError(f"Refresh failed: {data['error']}")

    new_access_token = data.get("access_token", "")
    if not new_access_token:
        raise RuntimeError("Refresh response has an empty access_token")

    return data


def merge_refreshed_tokens(old_tokens: dict, new_data: dict) -> dict:
    """
    Refresh Token Rotation: save the new refresh_token if the response includes one.
    Otherwise keep the old one — not every AS returns a new refresh token on rotation.
    """
    merged = old_tokens.copy()
    merged["access_token"] = new_data["access_token"]
    merged["expires_at"] = time.time() + new_data.get("expires_in", 3600)
    if "refresh_token" in new_data:
        merged["refresh_token"] = new_data["refresh_token"]
    return merged
```

---

## 15. Concurrent Refresh Lock: Preventing Multiple Parallel Refreshes

```python
import asyncio

_refresh_lock = asyncio.Lock()

async def get_valid_access_token(
    account: str,
    token_endpoint: str,
    client_id: str,
) -> str:
    """
    Return a valid access_token.
    If expired, refresh (with a lock to prevent concurrent rotation burn).
    """
    async with _refresh_lock:
        tokens = load_tokens(account)
        if tokens is None:
            raise RuntimeError("Not logged in — complete OAuth authorization first")

        if not is_token_expired(tokens):
            return tokens["access_token"]

        refresh_token = tokens.get("refresh_token")
        if not refresh_token:
            delete_tokens(account)
            raise RuntimeError("No refresh token — re-authorization required")

        new_data = await refresh_access_token(token_endpoint, client_id, refresh_token)
        merged = merge_refreshed_tokens(tokens, new_data)
        save_tokens(account, merged)
        return merged["access_token"]
```

> Multi-process environments: replace `asyncio.Lock` with a Redis or database lock. Without that, two processes hitting the same rotated refresh token in parallel both get `invalid_grant`.

---

## 16. Calling MCP: JSON-RPC Errors Live Inside HTTP 200

MCP uses JSON-RPC 2.0. HTTP 200 can still carry an `"error"` field in the response body.

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
        raise TokenExpiredError("Access token expired — refresh needed")
    resp.raise_for_status()

    data = resp.json()
    assert data.get("jsonrpc") == "2.0", "Not a valid JSON-RPC response"

    if "error" in data:
        err = data["error"]
        raise RuntimeError(
            f"MCP tool error [{err.get('code')}]: {err.get('message')}"
        )

    if "result" not in data:
        raise RuntimeError("JSON-RPC response has neither result nor error")

    return data["result"]


class TokenExpiredError(Exception):
    pass
```

Wrapper that refreshes on 401 and retries once:

```python
async def call_mcp_tool_with_retry(
    mcp_url: str,
    account: str,
    token_endpoint: str,
    client_id: str,
    tool_name: str,
    arguments: dict,
) -> dict:
    """Call an MCP tool, refresh on 401, retry once only."""
    for attempt in range(2):
        access_token = await get_valid_access_token(account, token_endpoint, client_id)
        try:
            return await call_mcp_tool(mcp_url, access_token, tool_name, arguments)
        except TokenExpiredError:
            if attempt == 1:
                # Still 401 after refresh — clear tokens and force re-auth
                delete_tokens(account)
                raise RuntimeError("Still 401 after refresh. Tokens cleared — please log in again.")
            # First 401: force expiry so the next loop iteration refreshes
            tokens = load_tokens(account) or {}
            tokens["expires_at"] = 0
            save_tokens(account, tokens)
```

> **Do not** do `while 401: refresh`. Refresh once. Second 401 clears the token.

---

## 17. Scopes: Logged In Is Not the Same as All Permissions

Fine-grained scopes beat one fat `trading` scope:

| Scope | Risk |
|-------|------|
| `quotes.read` | Low |
| `portfolio.read` | Low–medium |
| `orders.review` | Medium |
| `orders.place` | High |
| `cash.transfer` | Very high |

**Least Privilege principle:**

- Read before write  
- Review before place  
- Portfolio access without transfer access  

After the token exchange, verify the server actually granted the scopes you asked for:

```python
def verify_granted_scopes(requested: list[str], granted_scope_str: str) -> None:
    granted = set(granted_scope_str.split())
    missing = set(requested) - granted
    if missing:
        raise PermissionError(
            f"Server did not grant these scopes: {missing}. "
            "Check your app registration or whether the user denied partial permissions."
        )
```

---

## 18. Resource / Audience Binding (RFC 8707)

A token must be bound to a specific MCP resource. A token issued for a `quotes.read` API cannot be used to call the trading API.

```python
# Add the resource parameter to the authorization request
params["resource"] = "https://agent.example.com/mcp/trading"
```

**The MCP server must verify `aud`:**

```python
def verify_jwt_audience(payload: dict, expected_audience: str) -> None:
    aud = payload.get("aud")
    if isinstance(aud, str):
        aud = [aud]
    if expected_audience not in (aud or []):
        raise PermissionError(
            f"Token audience mismatch: expected {expected_audience}, got {aud}"
        )
```

---

## 19. MCP Server Token Verification: Overview

Verification flow:

```text
1. Parse Authorization: Bearer <token>
   ↓ Missing → 401 + WWW-Authenticate
2. Determine token type (JWT has "." separators; opaque does not)
   ↓ JWT → verify locally with JWKS
   ↓ Opaque → call Introspection Endpoint
3. Validate iss / aud / exp / nbf / algorithm / kid
4. Check scope per tool
   ↓ Insufficient → 403 insufficient_scope
5. Pass → execute the tool
```

---

## 20. JWT Verification Implementation

```python
import time
from typing import Any
import httpx
from jose import jwt, JWTError, ExpiredSignatureError
from jose.exceptions import JWKError

_jwks_cache: dict[str, Any] = {}
_jwks_fetched_at: float = 0
JWKS_CACHE_TTL = 3600  # Cache for 1 hour


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
    Verify JWT signature, issuer, audience, and expiry.
    Returns the decoded payload.
    Never set verify_signature=False.
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
                "verify_signature": True,  # Never change this to False
            },
        )
    except ExpiredSignatureError:
        raise PermissionError("Token has expired")
    except JWTError as e:
        raise PermissionError(f"JWT verification failed: {e}")

    return payload
```

---

## 21. Opaque Token Introspection

If the token you receive is not a JWT (no `.` separators), call the Introspection Endpoint:

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
        raise PermissionError("Token is invalid or expired (active != true)")

    # Validate audience and issuer
    expected_aud = "https://agent.example.com/mcp/trading"
    aud = result.get("aud")
    if isinstance(aud, str):
        aud = [aud]
    if expected_aud not in (aud or []):
        raise PermissionError(f"Introspection audience mismatch: {aud}")

    return result
```

---

## 22. Scope Enforcement at the Tool Level

Every high-risk tool on the MCP server checks scope before it executes:

```python
def require_scopes(token_scopes: str, *required: str) -> None:
    """
    token_scopes: the scope string from the token payload (space-separated)
    required: scopes the tool needs
    """
    granted = set(token_scopes.split())
    missing = [s for s in required if s not in granted]
    if missing:
        # Return a standard OAuth error; the client can prompt re-authorization
        raise PermissionError(
            f"insufficient_scope: missing {missing}. "
            f"Granted: {granted}"
        )


# Usage inside a tool handler
async def tool_place_order(token_payload: dict, order_params: dict) -> dict:
    require_scopes(token_payload.get("scope", ""), "orders.place")
    # ... order logic
```

---

## 23. Dynamic Client Registration

An Auth Server may expose a `registration_endpoint`. Public clients typically use `token_endpoint_auth_method=none` — no fixed `client_secret` required.

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
        "token_endpoint_auth_method": "none",  # Public client
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

    assert "client_id" in data, "Registration response missing client_id"
    return data
```

Save the registration against the issuer — a `client_id` registered with one AS is not valid for another:

```python
def save_client_registration(issuer: str, registration: dict) -> None:
    keyring.set_password(
        SERVICE_NAME,
        f"registration:{issuer}",
        json.dumps(registration),
    )
```

---

## 24. Review → Confirm → Execute

OAuth answers "did the user authorize this client?" It does **not** answer "did the user approve this specific trade?"

A model can misread "check on NVDA for me" as "buy NVDA now." High-risk tools must be split:

```text
review_equity_order  → preview only, no execution, returns review_id + summary
User confirms the summary (they see symbol / qty / price)
place_equity_order   → references review_id only (no symbol/qty retransmitted)
```

```python
import uuid
import time

# Server-side storage (illustrative — use a database in production)
_pending_reviews: dict[str, dict] = {}
REVIEW_TTL_SECONDS = 120  # Review is valid for 2 minutes


def create_review(
    user_id: str,
    symbol: str,
    side: str,
    quantity: float,
    order_type: str,
    limit_price: float | None = None,
) -> dict:
    """
    Create a review record with frozen parameters.
    Returns the summary shown to the user and the review_id.
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
        f"You are about to {'buy' if side == 'buy' else 'sell'} "
        f"{quantity} shares of {symbol}, "
        f"type: {order_type}"
        + (f", limit: ${limit_price:.2f}" if limit_price else "")
    )
    return {"review_id": review_id, "summary": summary}


def execute_from_review(review_id: str, user_id: str, idempotency_key: str) -> dict:
    """
    Execute an order using a review_id.
    All parameters come from the review record — external mutation is not allowed.
    """
    review = _pending_reviews.get(review_id)
    if not review:
        raise ValueError(f"Review {review_id} not found")
    if review["user_id"] != user_id:
        raise PermissionError("Review does not belong to this user")
    if review["used"]:
        raise ValueError("Review has already been used — cannot execute twice")
    if time.time() - review["created_at"] > REVIEW_TTL_SECONDS:
        raise ValueError("Review has expired — please review again")

    review["used"] = True  # Single-use

    # Submit to broker (illustrative)
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

## 25. Idempotency-Key: Preventing Duplicate Orders from Network Retries

```python
import hashlib

# Server-side processed set (use a database with TTL in production)
_processed_idempotency_keys: set[str] = set()


def generate_idempotency_key(review_id: str, user_id: str) -> str:
    """Generate a deterministic Idempotency-Key from review_id + user_id."""
    raw = f"{user_id}:{review_id}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def check_and_mark_idempotency(key: str) -> bool:
    """
    Returns True for first-time processing.
    Returns False for a duplicate request (return the cached result instead).
    """
    if key in _processed_idempotency_keys:
        return False
    _processed_idempotency_keys.add(key)
    return True
```

Review → Execute flow with idempotency:

```text
Client: review_equity_order(symbol, qty)
Server: returns review_id + summary
Client displays summary to user
User confirms
Client: place_equity_order(review_id, idempotency_key)
Server: validates review → executes order → marks key as used
Network retry: same key → returns cached result, does not re-submit
```

This is the same fail-closed approach as XingAI [ADR-028](https://github.com/xingaiapp/xingai-invest-ai/blob/main/docs/adr/028-robinhood-mcp-execution-gates.md) and the [xingai-robinhood-mcp](https://github.com/xingaiapp/xingai-robinhood-mcp) gateway: **the prompt is a request; the code is the gate.**

---

## 26. Do Not Forward User Tokens to Downstream Services

```text
Dangerous:
MCP Client → Access Token → MCP Server → forwards same token → Third-party API

Problems:
- Wrong audience (the token was minted for the MCP Server, not the third party)
- Downstream service receives a token it should never see
- Blurry audit boundary — who called the third party, and as whom?
```

Correct options:

```text
Option A (Service Credential):
MCP Server validates user token → confirms scope is sufficient → calls broker/internal API
with the server's own service credential

Option B (Token Exchange, RFC 8693):
MCP Server calls token_exchange_endpoint to swap the user token for one
with audience = the downstream API
```

```python
async def exchange_token_for_downstream(
    token_exchange_endpoint: str,
    subject_token: str,
    audience: str,
    client_id: str,
) -> str:
    """RFC 8693 Token Exchange — get a new token scoped to the downstream service."""
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

## 27. Token Revocation and Logout

```python
async def revoke_token(
    revocation_endpoint: str,
    token: str,
    token_type_hint: str,  # "access_token" or "refresh_token"
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
        # RFC 7009: even if the token does not exist, the server should return 200
        if resp.status_code not in (200, 400):
            resp.raise_for_status()


async def logout(
    account: str,
    revocation_endpoint: str,
    client_id: str,
) -> None:
    """Full logout: revoke server-side first, then delete local storage."""
    tokens = load_tokens(account)
    if tokens:
        # Revoke the refresh token first (revocation typically cascades to access token)
        rt = tokens.get("refresh_token")
        if rt:
            await revoke_token(revocation_endpoint, rt, "refresh_token", client_id)
        at = tokens.get("access_token")
        if at:
            await revoke_token(revocation_endpoint, at, "access_token", client_id)
    delete_tokens(account)
```

---

## 28. Log Safety: Never Record Credentials

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

## 29. Audit Records

Audit logs capture what happened — not the credentials themselves:

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
    Write an audit record. In production, write to an append-only store (DB / SIEM).
    Never include access_token, refresh_token, or code.
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
    # Simplified to a log call here; production writes to a database or SIEM
    logger.info("AUDIT %s", entry)
```

---

## 30. Publishing Protected Resource Metadata

The MCP server must publish its own metadata so clients can discover it.

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
    # ... normal processing
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

## 31. Defense in Depth in the Robinhood Case

Public materials show Agentic Trading uses a **separate Agentic Account**, not unlimited access to the main account:

1. **Account isolation** — clear risk boundary; blast radius is contained  
2. **Permission isolation** — trading, banking, and credit card should not share one unlimited token  
3. **Visible activity** — who, when, which client, confirmed or not, and what was the result  
4. **Revocable at the vendor** — revoke on the vendor side, not just "log out" from the agent  

These four principles are worth copying for any MCP you build, not just brokerage ones:

```text
Separate account / separate credential  →  contain blast radius
Fine-grained scopes                     →  least privilege
Visible activity log                    →  post-incident audit
Vendor-side revocation                  →  immediate invalidation
```

---

## 32. Ten Common Beginner Mistakes

| Mistake | Consequence | Fix |
|---------|-------------|-----|
| Password in MCP config | Full account exposure | Use OAuth |
| Client secret in desktop app | Extractable by anyone | Public client + PKCE |
| Skip state validation | CSRF | Random state + constant-time compare |
| Guess the token endpoint directly | Easy to get wrong | Metadata discovery |
| Trust HTTP 200 alone | Empty token persisted | Validate every field |
| Log tokens | Credential leak | Redact |
| Long-lived access tokens | Large leak window | Short access + refresh |
| Infinite 401 retry loop | Infinite loop | One refresh, then clear |
| Mutable params after review | Bypass confirmation | Freeze params in review_id |
| Skip audience check | Cross-service token abuse | Verify `aud` |

---

## Summary

**Production checklist**

**Client side:**

- [ ] Discover endpoints from Resource Metadata + AS Metadata (never hard-code)  
- [ ] PKCE S256, generate a fresh verifier for every authorization  
- [ ] State for CSRF, constant-time compare  
- [ ] Redirect URI strict match  
- [ ] After token exchange, validate non-empty value, correct type, sane `expires_in`  
- [ ] Store tokens in keychain — never in a plaintext file  
- [ ] `expires_at` = `now + expires_in`, refresh 60 seconds early  
- [ ] Lock concurrent refresh attempts  
- [ ] On 401, refresh once only; second 401 clears tokens  
- [ ] Logout: revoke server-side before deleting local storage  
- [ ] Redact credentials in all logs  

**Server side:**

- [ ] No Bearer → 401 + `WWW-Authenticate` pointing at Resource Metadata  
- [ ] JWT → JWKS signature check, validate `iss` / `aud` / `exp` / `nbf` / algorithm / kid  
- [ ] Opaque token → introspection, require `active: true`  
- [ ] Scope check per tool; insufficient → 403 `insufficient_scope`  
- [ ] Do not accept tokens in query strings  
- [ ] Do not forward user tokens to downstream services  
- [ ] Rate limit high-risk tools  
- [ ] Publish your own Protected Resource Metadata  
- [ ] Complete audit records (without credentials)  

**High-risk tools:**

- [ ] Isolated account  
- [ ] Review → Execute; review expires quickly and is single-use  
- [ ] Execute reads params from the review record — external mutation not permitted  
- [ ] Idempotency-Key prevents duplicate submissions from network retries  
- [ ] Daily / per-order limits  
- [ ] Explicit user confirmation (user sees symbol / qty / price)  
- [ ] Can be paused and revoked  

Full hands-on checklist at the end of the [lab article](2026-07-12-mcp-oauth-pkce-lab.md).

---

One diagram:

```text
Metadata discovery → OAuth 2.1 → PKCE → short-lived access token
  → minimal scopes → resource/audience binding
  → isolated agent account → review + user confirmation
  → limits / idempotency / audit → revoke at any time
```

One sentence:

> Don't give the agent a password. Don't give a token unlimited power. Don't treat a single login as approval for every high-risk action. Every execution must be limited, confirmable, auditable, and revocable.

When you evaluate a new MCP, ask these questions first:

1. Why does it want my password instead of a browser OAuth flow?  
2. What is the token's audience and scope?  
3. What can an attacker do if this token leaks?  
4. Do high-risk tools require separate, explicit confirmation?  
5. Can I revoke this agent at the vendor's side immediately?  

If you cannot answer those clearly, do not let it near real money, production data, or core systems.

---

## Next Steps

Build a runnable Auth Server + MCP Server + Client with a **simulated** portfolio (no real broker):

→ [Build an OAuth 2.1 + PKCE MCP project from scratch](2026-07-12-mcp-oauth-pkce-lab.md)

See the same pattern applied outside brokerage, to insurance claims adjudication, as a runnable POC with a settlement-authority policy layer instead of a notional cap:

→ [Claims MCP OAuth POC](https://github.com/xingaiapp/xingai-enterprise-ai-pocs/tree/main/pocs/claims-mcp-oauth-poc) — includes its own `docs/mcp-auth-deep-dive.md` mapping every concept from this article onto real claims-domain code

Production topology and fail-closed gateway:

→ [How MCP Works in Production](../articles/2026-07-11-mcp-in-production-robinhood-case.md)

---

## Disclaimer

Code in this guide is for teaching and architecture demonstration. It omits distributed locks, database transactions, HSM integration, full SSRF defenses, DPoP, complete Token Exchange implementation, cloud secret managers, compliance audit systems, and the error handling and monitoring expected in production.

Robinhood's actual endpoints, tool names, scopes, token formats, and auth flows may change with product updates. Always follow live MCP metadata, official documentation, and the current client implementation for real integrations. Example URLs in this article (`agent.example.com`, `auth.example.com`) are illustrative teaching addresses — they do not represent any real service.

Content is provided for informational and educational purposes only, on an "as is" basis. It does not constitute investment, legal, or security compliance advice. You are responsible for evaluating and managing risks in your own use. Connecting real money accounts to home-built MCP systems that have not been thoroughly security audited is not encouraged.

The hands-on lab (simulated data only, no real broker) continues here: [Build an OAuth 2.1 + PKCE MCP project from scratch](2026-07-12-mcp-oauth-pkce-lab.md).

---

**Author:** Xing Wang  
**Published:** 2026-07-12  
**Tags:** mcp, oauth, pkce, jwt, security, education
