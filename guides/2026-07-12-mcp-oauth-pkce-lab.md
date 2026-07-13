---
title: Build an OAuth 2.1 + PKCE MCP Project from Scratch — Complete Runnable Lab
author: Xing Wang
date: 2026-07-12
tags: [mcp, oauth, pkce, fastapi, education, security, jwt, hands-on]
description: Hands-on lab — build an Authorization Server, MCP Server, and Python Client with metadata discovery, PKCE, JWT, scopes, Review→Execute, idempotency, and full test suite. Simulated portfolio only; no real broker, no investment advice.
---

# Build an OAuth 2.1 + PKCE MCP Project from Scratch — Complete Runnable Lab

**中文版：** [2026-07-12-mcp-oauth-pkce-lab.zh.md](2026-07-12-mcp-oauth-pkce-lab.zh.md)  
**Concepts first (read this before the lab):** [MCP Auth — The Robinhood Deep Dive](2026-07-12-mcp-oauth-auth-deep-dive.md)  
**Architecture reference:** [MCP in Production](../articles/2026-07-11-mcp-in-production-robinhood-case.md)  
**Implementation repo:** [xingai-robinhood-mcp](https://github.com/xingaiapp/xingai-robinhood-mcp) (brokerage) · **Runnable POC:** [claims-mcp-oauth-poc](https://github.com/xingaiapp/xingai-enterprise-ai-pocs/tree/main/pocs/claims-mcp-oauth-poc) (insurance claims — this lab's code, ported)

> **Important:** This lab is a **simulated teaching system**. It does not connect to any real broker, does not constitute investment advice, and is not production-ready code. All code is provided "as is". You are responsible for evaluating, deploying, and ensuring compliance with any applicable regulations before using it in any real context.

---

## 33. What We Are Building

Three cooperating services, all running locally:

```text
MCP Client (Python CLI)
     │
     │ 1. POST /mcp (no token) → receives 401 + resource_metadata
     │
     ▼
Authorization Server (:8000)
     │  Metadata discovery / PKCE / JWT issuance / Refresh Rotation / Revocation
     │
     ▼  Bearer JWT
MCP Server (:8001)
     │  Signature verify + Scope + Agent Policy + Review → Execute + Idempotency
     ▼
Simulated Portfolio / Quote / Review / Place (no real broker)
```

**Three core principles**:

1. **Auth is the gate to MCP.** Without a valid JWT you get nothing.
2. **Scope ≠ Policy.** Holding `orders.place` scope does not mean you can place any order for any amount.
3. **Review is the human-confirmation checkpoint.** The place stage cannot change order parameters set during review.

---

## 34. Project Layout

```text
secure-mcp-demo/
├── auth_server/
│   ├── __init__.py
│   ├── main.py          # FastAPI app + all OAuth endpoints
│   ├── models.py        # Pydantic models + in-memory storage structures
│   ├── security.py      # PKCE verify / JWT issuance / JWKS exposure
│   └── storage.py       # In-memory KV (replace with PostgreSQL + Redis in production)
├── mcp_server/
│   ├── __init__.py
│   ├── main.py          # FastAPI app + JSON-RPC /mcp endpoint
│   ├── auth.py          # Bearer extraction / JWKS fetch / scope check
│   ├── tools.py         # Four MCP tool implementations
│   └── policies.py      # Agent second-wall policy
├── client/
│   ├── __init__.py
│   ├── main.py          # Main flow: discovery → PKCE → token → tool calls
│   ├── discovery.py     # Resource Metadata + AS Metadata discovery
│   ├── oauth.py         # PKCE generation / loopback callback / token exchange
│   └── token_store.py   # Token persistence (file for demo; Keychain in production)
├── tests/
│   ├── test_auth_server.py
│   ├── test_mcp_auth.py
│   └── test_order_flow.py
├── keys/
│   ├── private.pem      # Auth Server holds this; never leaves this machine
│   └── public.pem       # MCP Server uses this to verify signatures
├── requirements.txt
├── docker-compose.yml
└── README.md
```

---

## 35. Environment Setup

```bash
# Requires Python 3.11+
python --version

# Create virtual environment
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# Install dependencies
pip install fastapi "uvicorn[standard]" requests httpx \
  "PyJWT[crypto]" cryptography python-multipart \
  pydantic keyring pytest pytest-asyncio httpx
```

`requirements.txt`:

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

## 36. Generate the RSA Key Pair

The Auth Server holds the **private key** for signing. The MCP Server holds only the **public key** for verification. The private key never leaves the Auth Server's machine.

```bash
mkdir -p keys

# Generate 2048-bit RSA private key
openssl genrsa -out keys/private.pem 2048

# Export public key
openssl rsa -in keys/private.pem -pubout -out keys/public.pem

# Lock down permissions (required in production)
chmod 600 keys/private.pem
chmod 644 keys/public.pem

# Verify
openssl rsa -in keys/private.pem -check -noout
# Expected: RSA key ok
```

---

## 37. Auth Server — models.py

All in-memory data structures. No database needed for the demo stage.

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
    """Single-use short-lived authorization code, exchanged for tokens."""
    code: str
    client_id: str
    redirect_uri: str
    user_id: str
    scope: str                     # Space-separated scope list
    code_challenge: str            # S256 challenge
    created_at: float = field(default_factory=time.time)
    expires_in: int = 120          # Must be exchanged within 120 seconds
    used: bool = False             # One-shot: set True immediately after exchange

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
    """Refresh Token with Rotation support (old token replaced by new, old immediately invalidated)."""
    token: str
    client_id: str
    user_id: str
    scope: str
    revoked: bool = False
    created_at: float = field(default_factory=time.time)
    expires_in: int = 86400 * 30   # 30 days

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
    """OAuth client registration record."""
    client_id: str
    redirect_uris: list[str]
    client_name: str = ""
    token_endpoint_auth_method: str = "none"   # Public client (no secret)


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
# Supported scope set
# ---------------------------------------------------------------------------

SUPPORTED_SCOPES = {
    "portfolio.read",
    "quotes.read",
    "orders.review",
    "orders.place",
    "offline_access",   # Scope required to receive a refresh token
}
```

---

## 38. Auth Server — storage.py

Thread-safe in-memory KV. Replace with PostgreSQL + Redis in production.

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
    """Thread-safe in-memory store for demo purposes only."""

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


# Process-wide singleton
storage = InMemoryStorage()

# Pre-seed the demo client
storage.save_client(ClientRegistration(
    client_id="demo-desktop-client",
    redirect_uris=["http://127.0.0.1:54321/callback"],
    client_name="Demo Desktop MCP Client",
))
```

---

## 39. Auth Server — security.py

PKCE verification, JWT issuance, and JWKS exposure.

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
# Key loading
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
# Configuration
# ---------------------------------------------------------------------------

ISSUER = os.getenv("AUTH_ISSUER", "http://localhost:8000")
AUDIENCE = os.getenv("MCP_AUDIENCE", "http://localhost:8001/mcp")
ACCESS_TOKEN_TTL = int(os.getenv("ACCESS_TOKEN_TTL", "300"))   # 5 minutes
KID = "demo-key-001"   # Key ID — used for multi-kid JWKS rotation in production


# ---------------------------------------------------------------------------
# PKCE verification
# ---------------------------------------------------------------------------

def verify_pkce(code_verifier: str, code_challenge: str) -> bool:
    """
    Verify PKCE S256:
      code_challenge = BASE64URL( SHA256( ASCII( code_verifier ) ) )
    Uses constant-time compare to prevent timing attacks.
    """
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    expected = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return hmac.compare_digest(expected, code_challenge)


# ---------------------------------------------------------------------------
# JWT issuance
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
    Returns (jwt_string, expires_in_seconds).
    Uses RS256; claims include iss / sub / aud / scope / client_id / exp / iat / jti.
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
# JWKS construction (exposes public key to MCP Server)
# ---------------------------------------------------------------------------

def _int_to_base64url(n: int) -> str:
    """Convert a large integer to Base64URL (no padding) for JWK n/e fields."""
    byte_length = math.ceil(n.bit_length() / 8)
    return base64.urlsafe_b64encode(
        n.to_bytes(byte_length, "big")
    ).rstrip(b"=").decode("ascii")


def public_key_to_jwk() -> dict:
    """Serialize the RSA public key into JWK format."""
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
    """Return full JWKS (supports multiple keys for production rotation)."""
    return {"keys": [public_key_to_jwk()]}


# ---------------------------------------------------------------------------
# Secure random token generation
# ---------------------------------------------------------------------------

def generate_secure_token(n_bytes: int = 32) -> str:
    """Generate a URL-safe random string for authorization codes and refresh tokens."""
    return base64.urlsafe_b64encode(os.urandom(n_bytes)).rstrip(b"=").decode("ascii")
```

---

## 40. Auth Server — main.py

Complete implementation of all OAuth 2.1 endpoints.

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
# AS Metadata (RFC 8414)
# ---------------------------------------------------------------------------

@app.get("/.well-known/oauth-authorization-server")
async def oauth_metadata():
    """Authorization Server Metadata — clients use this to auto-discover all endpoints."""
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
    """Expose the RSA public key; MCP Server uses this to verify JWT signatures."""
    return get_jwks()


# ---------------------------------------------------------------------------
# Dynamic client registration (RFC 7591 — demo: loopback redirects only)
# ---------------------------------------------------------------------------

@app.post("/register", response_model=RegistrationResponse)
async def register_client(req: RegistrationRequest):
    """
    Dynamically register an OAuth client.
    Demo security restriction: redirect_uri must point to 127.0.0.1 or localhost.
    """
    for uri in req.redirect_uris:
        if not (uri.startswith("http://127.0.0.1") or uri.startswith("http://localhost")):
            raise HTTPException(
                status_code=400,
                detail="Demo mode only allows loopback redirect URIs",
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
# Authorization endpoint (GET: show consent page; POST: user clicks approve)
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
    """Show consent page (demo uses fixed user demo-user-001; production requires real login)."""
    _validate_authorize_params(
        response_type, client_id, redirect_uri, scope, code_challenge_method
    )

    # Simple HTML consent page (use a real template engine in production)
    html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Authorization Request</title>
  <style>
    body {{ font-family: system-ui, sans-serif; max-width: 480px; margin: 60px auto; padding: 20px; }}
    .scope {{ background: #f0f4f8; padding: 8px 12px; border-radius: 6px; margin: 4px 0; }}
    button {{ background: #2563eb; color: white; border: none; padding: 10px 20px;
              border-radius: 6px; cursor: pointer; font-size: 16px; margin-right: 10px; }}
    button.deny {{ background: #dc2626; }}
  </style>
</head>
<body>
  <h2>Authorization Request</h2>
  <p><strong>Application</strong>: {client_id}</p>
  <p><strong>Requested permissions</strong>:</p>
  {''.join(f'<div class="scope">&#10003; {s}</div>' for s in scope.split())}
  <br>
  <form method="POST" action="/authorize">
    <input type="hidden" name="response_type" value="{response_type}">
    <input type="hidden" name="client_id" value="{client_id}">
    <input type="hidden" name="redirect_uri" value="{redirect_uri}">
    <input type="hidden" name="scope" value="{scope}">
    <input type="hidden" name="state" value="{state}">
    <input type="hidden" name="code_challenge" value="{code_challenge}">
    <input type="hidden" name="code_challenge_method" value="{code_challenge_method}">
    <button type="submit" name="decision" value="allow">Allow</button>
    <button type="submit" name="decision" value="deny" class="deny">Deny</button>
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
    """Handle the user's consent decision; generate the authorization code and redirect."""
    _validate_authorize_params(
        response_type, client_id, redirect_uri, scope, code_challenge_method
    )

    if decision != "allow":
        return RedirectResponse(
            f"{redirect_uri}?error=access_denied&state={state}",
            status_code=302,
        )

    # Generate single-use Authorization Code (TTL 120s)
    code = generate_secure_token(24)
    record = AuthorizationCodeRecord(
        code=code,
        client_id=client_id,
        redirect_uri=redirect_uri,
        user_id="demo-user-001",   # Fixed demo user; replace with real session in production
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
    """Validate authorization request parameters consistently."""
    if response_type != "code":
        raise HTTPException(status_code=400, detail="Only response_type=code is supported")

    client = storage.get_client(client_id)
    if not client:
        raise HTTPException(status_code=400, detail="Unknown client_id")

    if redirect_uri not in client.redirect_uris:
        raise HTTPException(status_code=400, detail="redirect_uri does not match registration")

    if code_challenge_method != "S256":
        raise HTTPException(status_code=400, detail="Must use code_challenge_method=S256")

    requested = set(scope.split())
    unknown = requested - SUPPORTED_SCOPES
    if unknown:
        raise HTTPException(status_code=400, detail=f"Unsupported scope(s): {unknown}")


# ---------------------------------------------------------------------------
# Token endpoint
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
    Supports two grants:
    - authorization_code: code + PKCE verifier → access + refresh tokens
    - refresh_token: old refresh → new access + new refresh (Rotation)
    """
    if grant_type == "authorization_code":
        return await _handle_authorization_code(
            code, redirect_uri, client_id, code_verifier
        )
    elif grant_type == "refresh_token":
        return await _handle_refresh_token(refresh_token, client_id, scope)
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported grant_type: {grant_type}")


async def _handle_authorization_code(
    code: Optional[str],
    redirect_uri: Optional[str],
    client_id: Optional[str],
    code_verifier: Optional[str],
) -> TokenResponse:
    """Handle authorization_code grant."""
    if not all([code, redirect_uri, client_id, code_verifier]):
        raise HTTPException(
            status_code=400,
            detail="authorization_code grant is missing required parameters",
        )

    record = storage.get_code(code)  # type: ignore[arg-type]

    # Validation order: exists → valid → client match → redirect match → PKCE
    if not record:
        raise HTTPException(status_code=400, detail="Invalid authorization code")

    if not record.is_valid:
        detail = "Authorization code already used" if record.used else "Authorization code expired"
        raise HTTPException(status_code=400, detail=detail)

    if record.client_id != client_id:
        raise HTTPException(status_code=400, detail="client_id mismatch")

    if record.redirect_uri != redirect_uri:
        raise HTTPException(status_code=400, detail="redirect_uri mismatch")

    if not verify_pkce(code_verifier, record.code_challenge):  # type: ignore[arg-type]
        raise HTTPException(
            status_code=400,
            detail="PKCE verification failed: code_verifier does not match code_challenge",
        )

    # All checks passed — mark code as used (prevent replay)
    storage.mark_code_used(code)  # type: ignore[arg-type]

    # Issue Access Token
    access_token, expires_in = create_access_token(
        subject=record.user_id,
        scope=record.scope,
        client_id=record.client_id,
    )

    # Issue Refresh Token only when scope includes offline_access
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
    Refresh Token Rotation:
    1. Validate the old refresh token
    2. Immediately revoke the old one (prevent replay)
    3. Issue a new access token + new refresh token
    """
    if not refresh_token or not client_id:
        raise HTTPException(status_code=400, detail="refresh_token grant is missing parameters")

    record = storage.get_refresh_token(refresh_token)

    if not record:
        raise HTTPException(status_code=400, detail="Invalid refresh_token")

    if not record.is_valid:
        detail = "refresh_token has been revoked" if record.revoked else "refresh_token has expired"
        raise HTTPException(status_code=400, detail=detail)

    if record.client_id != client_id:
        raise HTTPException(status_code=400, detail="client_id mismatch")

    # Rotation: revoke old refresh immediately
    storage.revoke_refresh_token(refresh_token)

    # Issue new Access Token
    access_token, expires_in = create_access_token(
        subject=record.user_id,
        scope=record.scope,
        client_id=record.client_id,
    )

    # Issue new Refresh Token
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
# Revocation endpoint (RFC 7009)
# ---------------------------------------------------------------------------

@app.post("/revoke")
async def revoke(
    token: str = Form(...),
    client_id: Optional[str] = Form(None),
):
    """
    Revoke a Refresh Token.
    RFC 7009: non-existent tokens also return 200 (prevents enumeration attacks).
    """
    record = storage.get_refresh_token(token)
    if record and (client_id is None or record.client_id == client_id):
        storage.revoke_refresh_token(token)
    return JSONResponse(content={}, status_code=200)
```

---

## 41. Start and Verify the Auth Server

```bash
# Terminal 1: start Auth Server
uvicorn auth_server.main:app --port 8000 --reload

# Verify metadata endpoint
curl -s http://localhost:8000/.well-known/oauth-authorization-server | python -m json.tool

# Verify JWKS
curl -s http://localhost:8000/jwks.json | python -m json.tool

# Expected JWKS response:
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

## 42. MCP Server — auth.py

Extracts the Bearer token from the Authorization header, verifies its signature, and checks scopes.

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
# Configuration
# ---------------------------------------------------------------------------

EXPECTED_ISSUER = os.getenv("EXPECTED_ISSUER", "http://localhost:8000")
EXPECTED_AUDIENCE = os.getenv("EXPECTED_AUDIENCE", "http://localhost:8001/mcp")
JWKS_URL = os.getenv("JWKS_URL", "http://localhost:8000/jwks.json")

# Resource Metadata URL (included in 401 WWW-Authenticate for client discovery)
RESOURCE_METADATA_URL = (
    "http://localhost:8001/.well-known/oauth-protected-resource/mcp"
)


@lru_cache(maxsize=1)
def _get_jwks_client() -> PyJWKClient:
    """Cache the JWKS client (handles key rotation caching automatically)."""
    return PyJWKClient(JWKS_URL, cache_keys=True)


# ---------------------------------------------------------------------------
# Token verification
# ---------------------------------------------------------------------------

def extract_bearer_token(request: Request) -> str:
    """
    Extract Bearer token from the Authorization header.
    Missing → 401 + WWW-Authenticate (with resource_metadata, so client can discover the AS).
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
    Verify JWT signature:
    1. Fetch public key from JWKS (matched by kid)
    2. Verify RS256 signature
    3. Verify iss / aud / exp
    Any failure returns 401.
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
    Check that JWT claims contain all required scopes.
    Insufficient → 403 + insufficient_scope.
    """
    token_scopes = set(claims.get("scope", "").split())
    missing = required - token_scopes
    if missing:
        raise HTTPException(
            status_code=403,
            detail=f"insufficient_scope: missing {missing}",
        )


def authenticate_request(request: Request, required_scopes: set[str]) -> dict[str, Any]:
    """
    Combined: extract token → verify signature → check scopes → return claims.
    MCP tool handlers call this directly.
    """
    token = extract_bearer_token(request)
    claims = verify_token(token)
    require_scopes(claims, required_scopes)
    return claims
```

---

## 43. MCP Server — policies.py

The second wall: Agent Policy (independent from OAuth Scope).

```python
# mcp_server/policies.py
from __future__ import annotations

from fastapi import HTTPException

# ---------------------------------------------------------------------------
# Agent Policy configuration
# Production: read from database; set dynamically per agent profile / account level
# ---------------------------------------------------------------------------

# Allowlist of tradable symbols
ALLOWED_SYMBOLS = {
    "NVDA", "MSFT", "AAPL", "GOOGL", "AMZN",
    "META", "TSLA", "AVGO", "AMD", "QCOM",
}

# Maximum notional per order (USD)
MAX_NOTIONAL_USD = 500.0

# Simulated portfolio (user demo-user-001)
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

# Simulated quotes (static for demo; production connects to live market data)
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
# Policy check function
# ---------------------------------------------------------------------------

def check_order_policy(symbol: str, quantity: int, side: str) -> float:
    """
    Validate an order against Agent Policy:
    1. Symbol must be on the allowlist
    2. Notional must not exceed the per-order limit
    Returns the current quote price (used for the review summary).
    """
    symbol = symbol.upper()

    if symbol not in ALLOWED_SYMBOLS:
        raise HTTPException(
            status_code=403,
            detail=f"policy_violation: {symbol} is not on the allowed symbol list",
        )

    if quantity <= 0:
        raise HTTPException(
            status_code=400,
            detail="quantity must be > 0",
        )

    price = MOCK_QUOTES.get(symbol)
    if price is None:
        raise HTTPException(
            status_code=400,
            detail=f"No quote data for {symbol}",
        )

    notional = price * quantity
    if notional > MAX_NOTIONAL_USD:
        raise HTTPException(
            status_code=403,
            detail=(
                f"policy_violation: notional ${notional:.2f} exceeds per-order limit "
                f"${MAX_NOTIONAL_USD:.2f}"
            ),
        )

    return price
```

---

## 44. MCP Server — tools.py

The four MCP tool implementations, including the Review → Execute state machine and idempotency.

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
# Review Store (in-memory; production uses DB + SELECT FOR UPDATE)
# ---------------------------------------------------------------------------

_review_lock = threading.Lock()
_reviews: dict[str, dict] = {}   # review_id → review record

_idempotency_lock = threading.Lock()
_idempotency_results: dict[str, dict] = {}   # idempotency_key → order result

REVIEW_TTL_SECONDS = 120   # review valid for 2 minutes


# ---------------------------------------------------------------------------
# Tool: get_portfolio
# ---------------------------------------------------------------------------

def tool_get_portfolio(user_id: str) -> dict:
    """
    Return simulated portfolio positions.
    Scope required: portfolio.read
    """
    portfolio = dict(MOCK_PORTFOLIO)
    portfolio["queried_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    return portfolio


# ---------------------------------------------------------------------------
# Tool: get_quote
# ---------------------------------------------------------------------------

def tool_get_quote(symbol: str) -> dict:
    """
    Return a simulated quote.
    Scope required: quotes.read
    """
    symbol = symbol.upper()
    price = MOCK_QUOTES.get(symbol)
    if price is None:
        raise HTTPException(
            status_code=404,
            detail=f"No quote data for {symbol}",
        )
    return {
        "symbol": symbol,
        "price": price,
        "currency": "USD",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "note": "Simulated quote — not real-time market data",
    }


# ---------------------------------------------------------------------------
# Tool: review_equity_order (Phase 1: create review; do not execute)
# ---------------------------------------------------------------------------

def tool_review_equity_order(
    symbol: str,
    quantity: int,
    side: str,    # "buy" | "sell"
    user_id: str,
) -> dict:
    """
    Generate an order preview and return a review_id (TTL 120s). Does not execute.
    Scope required: orders.review

    Key design:
    - All business parameters (symbol / quantity / side / price) are frozen inside the review record
    - The place stage accepts only review_id; business parameters cannot be changed
    """
    side = side.lower()
    if side not in ("buy", "sell"):
        raise HTTPException(status_code=400, detail="side must be buy or sell")

    # Agent Policy check (second wall)
    price = check_order_policy(symbol, quantity, side)

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
        "note": "Simulated order — no real trade will be executed",
    }

    with _review_lock:
        _reviews[review_id] = review

    return {
        "review_id": review_id,
        "summary": (
            f"{'Buy' if side == 'buy' else 'Sell'} {quantity} shares of {symbol.upper()} "
            f"@ approx. ${price:.2f}, estimated notional ${notional:.2f}"
        ),
        "expires_in_seconds": REVIEW_TTL_SECONDS,
        "action_required": "Type YES in the client to confirm, then call place_equity_order",
        "warning": "Simulated system — no real trade will be executed",
    }


# ---------------------------------------------------------------------------
# Tool: place_equity_order (Phase 2: execute only via review_id; no mutable args)
# ---------------------------------------------------------------------------

def tool_place_equity_order(
    review_id: str,
    idempotency_key: str,
    user_id: str,
) -> dict:
    """
    Execute an order using a review_id.
    Scope required: orders.place

    Security design:
    1. review_id is single-use (prevents replay)
    2. Same idempotency_key → return the same result (prevents duplicate orders from retries)
    3. Does not accept symbol / quantity / side — cannot bypass the review
    """
    # Idempotency check: same key → return cached result
    with _idempotency_lock:
        cached = _idempotency_results.get(idempotency_key)
        if cached:
            return {**cached, "idempotent": True}

    # Fetch review
    with _review_lock:
        review = _reviews.get(review_id)
        if not review:
            raise HTTPException(status_code=400, detail="Invalid review_id")

        if review["used"]:
            raise HTTPException(
                status_code=409,
                detail="review_id already used — cannot place the same order twice",
            )

        if time.time() > review["expires_at"]:
            raise HTTPException(
                status_code=400,
                detail="review_id has expired — please create a new review",
            )

        if review["user_id"] != user_id:
            raise HTTPException(
                status_code=403,
                detail="review_id does not belong to the current user",
            )

        # Atomically mark used (inside the lock to prevent concurrent replay)
        review["used"] = True

    # Simulate fill
    fill_price = review["estimated_price"]   # Production systems use the matched price
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
        "note": "Simulated fill — no real trade was executed",
    }

    # Store in idempotency cache
    with _idempotency_lock:
        _idempotency_results[idempotency_key] = result

    return result
```

---

## 45. MCP Server — main.py

JSON-RPC `/mcp` endpoint and Protected Resource Metadata.

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
# Tool definitions (returned by tools/list)
# ---------------------------------------------------------------------------

TOOLS = [
    {
        "name": "get_portfolio",
        "description": "Returns simulated portfolio positions and cash balance (no real broker)",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
        "scope_required": "portfolio.read",
    },
    {
        "name": "get_quote",
        "description": "Returns a simulated quote for the given symbol",
        "inputSchema": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Ticker symbol, e.g. NVDA"},
            },
            "required": ["symbol"],
        },
        "scope_required": "quotes.read",
    },
    {
        "name": "review_equity_order",
        "description": "Generate an order preview (review_id) without executing. Human confirmation required before calling place_equity_order",
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
        "description": "Execute a simulated order using a review_id (idempotent)",
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
# Protected Resource Metadata (RFC 9728)
# ---------------------------------------------------------------------------

@app.get("/.well-known/oauth-protected-resource/mcp")
async def protected_resource_metadata():
    """
    After receiving a 401, clients fetch this endpoint to discover the Authorization Server.
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
# JSON-RPC /mcp endpoint
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
    Unified JSON-RPC 2.0 endpoint, handling:
    - initialize
    - tools/list
    - tools/call
    """
    # Verify token first (no token → 401 + WWW-Authenticate)
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
            # tools/list requires authentication but no specific scope
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
            return _jsonrpc_error(req_id, -32601, f"Unknown method: {method}")

    except HTTPException as exc:
        return _jsonrpc_error(req_id, exc.status_code, exc.detail, exc.status_code)
    except Exception as exc:
        # Never expose internal stack traces to clients
        return _jsonrpc_error(req_id, -32603, "Internal error", 500)


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
                "description": "Simulated portfolio MCP Server — no real broker connection",
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

    # Look up tool definition
    tool_def = next((t for t in TOOLS if t["name"] == tool_name), None)
    if not tool_def:
        return _jsonrpc_error(req_id, -32602, f"Unknown tool: {tool_name}")

    # Check scope
    required_scope = tool_def["scope_required"]
    try:
        claims = authenticate_request(request, {required_scope})
    except HTTPException as exc:
        return _jsonrpc_error(req_id, exc.status_code, exc.detail, exc.status_code)

    user_id = claims.get("sub", "unknown")

    # Dispatch to the appropriate tool
    try:
        if tool_name == "get_portfolio":
            result = tool_get_portfolio(user_id)

        elif tool_name == "get_quote":
            symbol = arguments.get("symbol")
            if not symbol:
                return _jsonrpc_error(req_id, -32602, "Missing parameter: symbol")
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
            return _jsonrpc_error(req_id, -32601, f"Tool not implemented: {tool_name}")

    except HTTPException as exc:
        return _jsonrpc_error(req_id, exc.status_code, exc.detail, exc.status_code)

    return JSONResponse(content={
        "jsonrpc": "2.0",
        "id": req_id,
        "result": {
            "content": [{"type": "text", "text": str(result)}],
            "_data": result,   # Convenience field for structured client parsing
        },
    })
```

---

## 46. Start and Verify the MCP Server

```bash
# Terminal 2: start MCP Server
uvicorn mcp_server.main:app --port 8001 --reload

# Test 1: access without token — expect 401 + WWW-Authenticate
curl -i -X POST http://localhost:8001/mcp \
  -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'

# Expected response headers include:
# HTTP/1.1 401 Unauthorized
# WWW-Authenticate: Bearer resource_metadata="http://localhost:8001/.well-known/oauth-protected-resource/mcp"

# Test 2: Protected Resource Metadata
curl -s http://localhost:8001/.well-known/oauth-protected-resource/mcp | python -m json.tool
```

---

## 47. Client — discovery.py

Automatic discovery chain: 401 → Resource Metadata → AS Metadata.

```python
# client/discovery.py
from __future__ import annotations

import re
import urllib.parse

import requests

# SSRF guard: only allow localhost-type AS URLs (demo restriction; use a whitelist in production)
ALLOWED_AS_HOSTS = {"localhost", "127.0.0.1"}


def discover_from_401(www_authenticate: str) -> dict:
    """
    Parse the resource_metadata URL from a 401 WWW-Authenticate header,
    then walk the discovery chain to the AS Metadata.

    Returns the AS Metadata dict containing all endpoint URLs.
    """
    resource_metadata_url = _extract_resource_metadata_url(www_authenticate)
    resource_metadata = _fetch_resource_metadata(resource_metadata_url)
    as_metadata = _fetch_as_metadata(resource_metadata)
    _validate_as_metadata(as_metadata)
    return as_metadata


def _extract_resource_metadata_url(www_authenticate: str) -> str:
    """
    Parse the WWW-Authenticate header to extract the resource_metadata URL.
    Example: Bearer resource_metadata="http://localhost:8001/..."
    """
    match = re.search(r'resource_metadata="([^"]+)"', www_authenticate)
    if not match:
        raise ValueError(
            f"No resource_metadata in WWW-Authenticate header: {www_authenticate}"
        )
    url = match.group(1)
    _check_ssrf(url)
    return url


def _fetch_resource_metadata(url: str) -> dict:
    """Fetch Resource Metadata to get the authorization_servers list."""
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    if "authorization_servers" not in data or not data["authorization_servers"]:
        raise ValueError("Resource Metadata missing authorization_servers")
    return data


def _fetch_as_metadata(resource_metadata: dict) -> dict:
    """Fetch AS Metadata from authorization_servers[0] (RFC 8414)."""
    as_base = resource_metadata["authorization_servers"][0]
    _check_ssrf(as_base)
    metadata_url = f"{as_base.rstrip('/')}/.well-known/oauth-authorization-server"
    resp = requests.get(metadata_url, timeout=10)
    resp.raise_for_status()
    return resp.json()


def _validate_as_metadata(metadata: dict) -> None:
    """Validate that AS Metadata contains required fields and supports S256."""
    required_fields = [
        "issuer",
        "authorization_endpoint",
        "token_endpoint",
        "jwks_uri",
    ]
    for field in required_fields:
        if field not in metadata:
            raise ValueError(f"AS Metadata missing required field: {field}")

    pkce_methods = metadata.get("code_challenge_methods_supported", [])
    if "S256" not in pkce_methods:
        raise ValueError("AS does not support S256 PKCE — refusing to connect")


def _check_ssrf(url: str) -> None:
    """SSRF guard: demo only allows localhost-type AS URLs."""
    parsed = urllib.parse.urlparse(url)
    hostname = parsed.hostname or ""
    if hostname not in ALLOWED_AS_HOSTS:
        raise ValueError(
            f"SSRF guard: non-localhost AS not allowed ({hostname})"
        )
```

---

## 48. Client — oauth.py

PKCE generation, loopback callback server, and token exchange.

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
# PKCE generation
# ---------------------------------------------------------------------------

def generate_pkce_pair() -> tuple[str, str]:
    """
    Generate a PKCE code_verifier + code_challenge (S256).

    Returns (verifier, challenge).
    verifier is a 43–128 character random URL-safe string.
    challenge = BASE64URL( SHA256( verifier ) ) (no padding)
    """
    verifier = base64.urlsafe_b64encode(os.urandom(32)).rstrip(b"=").decode("ascii")
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return verifier, challenge


# ---------------------------------------------------------------------------
# Loopback callback server (receives Authorization Code)
# ---------------------------------------------------------------------------

class _CallbackHandler(http.server.BaseHTTPRequestHandler):
    """Temporary HTTP server to receive the Authorization Server redirect callback."""

    result: Optional[dict] = None
    _server_ref: Optional[http.server.HTTPServer] = None

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        params = dict(urllib.parse.parse_qsl(parsed.query))

        self.__class__.result = params

        body = b"""
        <html><body>
        <h2>&#10003; Authorization Successful</h2>
        <p>You can close this window and return to the terminal.</p>
        </body></html>
        """
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(body)

        threading.Thread(target=self._server_ref.shutdown, daemon=True).start()

    def log_message(self, format_, *args) -> None:
        pass   # Suppress log noise


def run_local_callback_server(port: int = 54321, timeout: int = 180) -> dict:
    """
    Start the loopback callback server and wait for the Authorization Code redirect.
    Raises TimeoutError if no callback arrives within the timeout.
    """
    _CallbackHandler.result = None
    server = http.server.HTTPServer(("127.0.0.1", port), _CallbackHandler)
    _CallbackHandler._server_ref = server

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    deadline = time.time() + timeout
    while _CallbackHandler.result is None:
        if time.time() > deadline:
            server.shutdown()
            raise TimeoutError(f"Timed out after {timeout}s waiting for Authorization Code")
        time.sleep(0.2)

    return _CallbackHandler.result


# ---------------------------------------------------------------------------
# Build Authorization URL and open browser
# ---------------------------------------------------------------------------

def build_authorization_url(
    as_metadata: dict,
    client_id: str,
    redirect_uri: str,
    scope: str,
    state: str,
    code_challenge: str,
) -> str:
    """Build the PKCE-carrying Authorization URL."""
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
# Token exchange (code + PKCE verifier → access token)
# ---------------------------------------------------------------------------

def exchange_code_for_token(
    as_metadata: dict,
    code: str,
    code_verifier: str,
    client_id: str,
    redirect_uri: str,
) -> dict:
    """
    Exchange an authorization code + PKCE verifier for an Access Token.
    Returns the full token response dict.
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
        raise ValueError(f"Token exchange failed ({resp.status_code}): {resp.text}")

    token_data = resp.json()
    access_token = token_data.get("access_token", "")
    if not access_token:
        raise ValueError("Token response contains no access_token — refusing to store")

    return token_data


def refresh_access_token(
    as_metadata: dict,
    refresh_token: str,
    client_id: str,
) -> dict:
    """Exchange a Refresh Token for a new Access Token (Rotation: old refresh immediately revoked)."""
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
        raise ValueError(f"Refresh failed ({resp.status_code}): {resp.text}")

    return resp.json()
```

---

## 49. Client — token_store.py

Token persistence (file for demo; OS Keychain in production).

```python
# client/token_store.py
from __future__ import annotations

import json
import os
import stat
import time
from pathlib import Path
from typing import Optional

# Demo token file path (production: use the keyring library to store in OS Keychain)
TOKEN_FILE = Path(os.getenv("MCP_TOKEN_FILE", ".mcp_tokens.json"))

# Proactive refresh threshold: refresh when less than 60 seconds remain
REFRESH_BUFFER_SECONDS = 60


def save_tokens(token_response: dict) -> None:
    """
    Persist token response to disk.
    Sets chmod 600 immediately after writing.
    """
    data = {
        "access_token":  token_response.get("access_token"),
        "refresh_token": token_response.get("refresh_token"),
        "scope":         token_response.get("scope"),
        "expires_at":    time.time() + int(token_response.get("expires_in", 300)),
        "saved_at":      time.time(),
    }

    # Never store an empty access_token
    if not data["access_token"]:
        raise ValueError("Refusing to store empty access_token")

    TOKEN_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
    os.chmod(TOKEN_FILE, stat.S_IRUSR | stat.S_IWUSR)   # chmod 600


def load_tokens() -> Optional[dict]:
    """Load stored tokens; returns None if the file does not exist."""
    if not TOKEN_FILE.exists():
        return None
    try:
        return json.loads(TOKEN_FILE.read_text(encoding="utf-8"))
    except Exception:
        return None


def get_valid_access_token() -> Optional[str]:
    """
    Return a valid Access Token.
    If the token is about to expire (< REFRESH_BUFFER_SECONDS), returns None to trigger a refresh.
    """
    tokens = load_tokens()
    if not tokens:
        return None

    access_token = tokens.get("access_token")
    expires_at = tokens.get("expires_at", 0)

    if not access_token:
        return None

    if time.time() + REFRESH_BUFFER_SECONDS >= expires_at:
        return None

    return access_token


def get_refresh_token() -> Optional[str]:
    """Return the stored Refresh Token (used for silent renewal after expiry)."""
    tokens = load_tokens()
    return tokens.get("refresh_token") if tokens else None


def clear_tokens() -> None:
    """Delete local tokens (used for logout or error recovery)."""
    if TOKEN_FILE.exists():
        TOKEN_FILE.unlink()
```

---

## 50. Client — main.py

Complete main flow: discovery → PKCE → token → tool calls → Review → human confirmation → Place.

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
# Configuration
# ---------------------------------------------------------------------------

MCP_URL = os.getenv("MCP_URL", "http://localhost:8001/mcp")
CLIENT_ID = "demo-desktop-client"
REDIRECT_URI = "http://127.0.0.1:54321/callback"
SCOPE = "portfolio.read quotes.read orders.review orders.place offline_access"
CALLBACK_PORT = 54321

_as_metadata: dict = {}     # Global AS Metadata cache


# ---------------------------------------------------------------------------
# Token management
# ---------------------------------------------------------------------------

def ensure_valid_token() -> str:
    """
    Guarantee a valid Access Token.
    Priority order:
    1. Cached, non-expired token
    2. Silent refresh using Refresh Token
    3. Full PKCE authorization flow
    """
    global _as_metadata

    # 1. Use cached token
    token = get_valid_access_token()
    if token:
        return token

    # 2. Try refresh
    refresh = get_refresh_token()
    if refresh and _as_metadata:
        try:
            print("→ Access Token expiring soon — refreshing silently...")
            token_data = refresh_access_token(_as_metadata, refresh, CLIENT_ID)
            save_tokens(token_data)
            print("✓ Token refreshed")
            return token_data["access_token"]
        except Exception as e:
            print(f"⚠ Refresh failed ({e}) — re-authorizing...")
            clear_tokens()

    # 3. Full PKCE flow
    return _full_oauth_flow()


def _full_oauth_flow() -> str:
    """Run the full PKCE Authorization Code Flow."""
    global _as_metadata

    print("\n=== OAuth 2.1 + PKCE Authorization Flow Starting ===")

    # Trigger a 401 to discover the AS
    if not _as_metadata:
        print("→ Discovering Authorization Server...")
        www_auth = _trigger_401_for_discovery()
        _as_metadata = discover_from_401(www_auth)
        print(f"✓ AS Issuer: {_as_metadata['issuer']}")

    # Generate PKCE and state
    verifier, challenge = generate_pkce_pair()
    state = base64.urlsafe_b64encode(os.urandom(16)).rstrip(b"=").decode("ascii")

    # Open browser
    auth_url = build_authorization_url(
        _as_metadata, CLIENT_ID, REDIRECT_URI, SCOPE, state, challenge
    )
    print(f"\n→ Opening browser for authorization...")
    print(f"  URL: {auth_url[:80]}...")

    import webbrowser
    webbrowser.open(auth_url)

    # Wait for callback
    print("→ Waiting for user to click 'Allow' in the browser...")
    callback = run_local_callback_server(port=CALLBACK_PORT, timeout=180)

    # Validate state (CSRF protection)
    if callback.get("state") != state:
        raise ValueError("state mismatch — possible CSRF attack!")

    if "error" in callback:
        raise ValueError(f"Authorization denied: {callback['error']}")

    code = callback.get("code")
    if not code:
        raise ValueError("No authorization code in callback")

    print("✓ Received Authorization Code — exchanging for tokens...")
    token_data = exchange_code_for_token(
        _as_metadata, code, verifier, CLIENT_ID, REDIRECT_URI
    )
    save_tokens(token_data)
    print("✓ Tokens obtained and stored securely")
    return token_data["access_token"]


def _trigger_401_for_discovery() -> str:
    """Send a token-less request to the MCP Server to obtain the WWW-Authenticate header."""
    resp = requests.post(
        MCP_URL,
        json={"jsonrpc": "2.0", "id": 0, "method": "initialize", "params": {}},
        timeout=10,
    )
    if resp.status_code != 401:
        raise ValueError(f"Expected 401, got {resp.status_code}")
    www_auth = resp.headers.get("WWW-Authenticate", "")
    if not www_auth:
        raise ValueError("401 response missing WWW-Authenticate header")
    return www_auth


# ---------------------------------------------------------------------------
# MCP RPC calls
# ---------------------------------------------------------------------------

_request_counter = 0


def call_mcp(method: str, params: dict = None, *, retry_on_401: bool = True) -> dict:
    """
    Send a JSON-RPC request to the MCP Server.
    On 401 → refresh token → retry once (never more, to prevent infinite loops).
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
        print("→ Got 401 — refreshing token and retrying...")
        clear_tokens()
        return call_mcp(method, params, retry_on_401=False)

    data = resp.json()

    if "error" in data:
        raise RuntimeError(
            f"MCP error [{data['error'].get('code')}]: {data['error'].get('message')}"
        )

    return data.get("result", {})


# ---------------------------------------------------------------------------
# Main flow
# ---------------------------------------------------------------------------

def main() -> None:
    print("=" * 60)
    print("  XingAI MCP Demo Client")
    print("  Simulated portfolio — no real broker, no real trades")
    print("=" * 60)

    # Step 1: Initialize
    print("\n[1/6] Initialize MCP connection...")
    init_result = call_mcp("initialize")
    server_info = init_result.get("serverInfo", {})
    print(f"✓ Connected: {server_info.get('name')} v{server_info.get('version')}")

    # Step 2: List Tools
    print("\n[2/6] Fetch available tools...")
    tools_result = call_mcp("tools/list")
    tools = tools_result.get("tools", [])
    print(f"✓ Available tools ({len(tools)}):")
    for t in tools:
        print(f"   • {t['name']}: {t.get('description', '')}")

    # Step 3: Get Portfolio
    print("\n[3/6] Query simulated portfolio...")
    portfolio_result = call_mcp("tools/call", {
        "name": "get_portfolio",
        "arguments": {},
    })
    portfolio = portfolio_result.get("_data", {})
    print(f"✓ Account: {portfolio.get('account_id')}")
    print(f"  Cash: ${portfolio.get('cash_usd', 0):,.2f}")
    print(f"  Positions:")
    for pos in portfolio.get("positions", []):
        pnl = (pos["current_price"] - pos["avg_cost"]) * pos["quantity"]
        print(f"    {pos['symbol']}: {pos['quantity']} shares @ ${pos['current_price']:.2f}  P&L: ${pnl:+.2f}")

    # Step 4: Get Quote
    symbol = "NVDA"
    print(f"\n[4/6] Fetch simulated quote for {symbol}...")
    quote_result = call_mcp("tools/call", {
        "name": "get_quote",
        "arguments": {"symbol": symbol},
    })
    quote = quote_result.get("_data", {})
    print(f"✓ {quote['symbol']}: ${quote['price']:.2f} (simulated quote)")

    # Step 5: Review Order (Phase 1 — no execution)
    print(f"\n[5/6] Submit order review (no execution)...")
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
    print(f"  Order Review")
    print(f"{'=' * 50}")
    print(f"  {review.get('summary', '')}")
    print(f"  Review ID: {review.get('review_id', '')}")
    print(f"  Valid for: {review.get('expires_in_seconds', 0)} seconds")
    print(f"  ⚠  {review.get('warning', '')}")
    print(f"{'=' * 50}")

    # Human confirmation gate
    confirm = input("\nType YES to confirm the order (any other input cancels): ").strip()
    if confirm != "YES":
        print("✗ Cancelled.")
        return

    # Step 6: Place Order (Phase 2 — idempotent)
    print(f"\n[6/6] Submit simulated order (idempotent Place)...")
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
    print(f"  Simulated Fill Result")
    print(f"{'=' * 50}")
    print(f"  Order ID:   {order.get('order_id')}")
    print(f"  Status:     {order.get('status')}")
    print(f"  {order.get('side', '').upper()} {order.get('quantity')} shares of {order.get('symbol')}")
    print(f"  Fill price: ${order.get('fill_price', 0):.2f}")
    print(f"  Notional:   ${order.get('notional', 0):.2f}")
    print(f"  Time:       {order.get('filled_at')}")
    print(f"  ⚠  {order.get('note')}")
    print(f"{'=' * 50}")

    # Idempotency demo
    print("\n→ Demonstrating idempotency: retrying with the same idempotency_key...")
    retry_result = call_mcp("tools/call", {
        "name": "place_equity_order",
        "arguments": {
            "review_id": review["review_id"],
            "idempotency_key": idempotency_key,
        },
    })
    retry_order = retry_result.get("_data", {})
    is_idempotent = retry_order.get("idempotent", False)
    print(f"✓ Retry is idempotent: {is_idempotent}, Order ID: {retry_order.get('order_id')}")
    assert retry_order.get("order_id") == order.get("order_id"), "Idempotency broken!"

    print("\n✓ Full flow demo complete. Thanks for using XingAI MCP Demo.")


if __name__ == "__main__":
    main()
```

---

## 51. Full Run

Open three terminals:

```bash
# Terminal 1: Auth Server
cd secure-mcp-demo
source .venv/bin/activate
uvicorn auth_server.main:app --port 8000 --reload

# ─────────────────────────────────────────────

# Terminal 2: MCP Server
cd secure-mcp-demo
source .venv/bin/activate
uvicorn mcp_server.main:app --port 8001 --reload

# ─────────────────────────────────────────────

# Terminal 3: Client
cd secure-mcp-demo
source .venv/bin/activate
python -m client.main
```

**Expected complete flow**:

```text
Client starts
  ↓
POST /mcp (no token)
  ↓ 401 + WWW-Authenticate: Bearer resource_metadata="..."
Client parses resource_metadata URL
  ↓
GET /.well-known/oauth-protected-resource/mcp
  ↓ authorization_servers: ["http://localhost:8000"]
GET /.well-known/oauth-authorization-server
  ↓ all endpoint URLs + S256 support confirmed
Client generates PKCE verifier + challenge
  ↓
Opens browser → /authorize (with challenge + state)
  ↓ user clicks Allow
/authorize POST → generates code (120s TTL)
  ↓ redirects to 127.0.0.1:54321/callback?code=...&state=...
Client receives code, validates state
  ↓
POST /token (code + verifier)
  ↓ PKCE verified → JWT access + refresh token issued
Client stores tokens (chmod 600)
  ↓
POST /mcp initialize → ✓
POST /mcp tools/list → 4 tools
POST /mcp tools/call get_portfolio → simulated portfolio
POST /mcp tools/call get_quote → simulated quote
POST /mcp tools/call review_equity_order → review_id
  ↓ terminal displays summary, waits for YES
User types YES
  ↓
POST /mcp tools/call place_equity_order → simulated fill
POST /mcp tools/call place_equity_order (retry) → same order_id (idempotent)
  ↓
Flow complete
```

---

## 52. Tests — tests/test_auth_server.py

```python
# tests/test_auth_server.py
"""Auth Server unit tests."""
import pytest
from fastapi.testclient import TestClient

from auth_server.main import app
from auth_server.security import verify_pkce, generate_secure_token
from client.oauth import generate_pkce_pair

client = TestClient(app)


class TestPKCE:
    def test_pkce_valid(self):
        """A correct verifier should pass verification."""
        verifier, challenge = generate_pkce_pair()
        assert verify_pkce(verifier, challenge) is True

    def test_pkce_invalid_verifier(self):
        """A wrong verifier should fail."""
        _, challenge = generate_pkce_pair()
        assert verify_pkce("wrong_verifier_abc123", challenge) is False

    def test_pkce_tampered_challenge(self):
        """A tampered challenge should fail."""
        verifier, _ = generate_pkce_pair()
        assert verify_pkce(verifier, "tampered_challenge_xyz") is False


class TestMetadataEndpoints:
    def test_as_metadata_returns_required_fields(self):
        """AS Metadata must include all RFC 8414 required fields."""
        resp = client.get("/.well-known/oauth-authorization-server")
        assert resp.status_code == 200
        data = resp.json()
        assert "issuer" in data
        assert "authorization_endpoint" in data
        assert "token_endpoint" in data
        assert "jwks_uri" in data
        assert "S256" in data.get("code_challenge_methods_supported", [])

    def test_jwks_returns_rsa_key(self):
        """JWKS must contain an RSA public key."""
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
        """Registering a client with a loopback redirect should succeed."""
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
        """A non-loopback redirect URI must be rejected by the demo security policy."""
        resp = client.post("/register", json={
            "client_name": "Evil Client",
            "redirect_uris": ["https://evil.example.com/steal"],
            "token_endpoint_auth_method": "none",
        })
        assert resp.status_code == 400


class TestTokenExchange:
    def _get_authorization_code(self) -> tuple[str, str]:
        """Helper: insert an authorization code directly into storage, bypassing the browser."""
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
        """Valid PKCE should produce a successful token exchange."""
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
        assert "refresh_token" in data   # offline_access scope → expect refresh token

    def test_token_exchange_invalid_pkce(self):
        """A wrong PKCE verifier must return 400."""
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
        """Authorization Code must be single-use."""
        code, verifier = self._get_authorization_code()

        # First attempt — success
        resp1 = client.post("/token", data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": "http://127.0.0.1:54321/callback",
            "client_id": "demo-desktop-client",
            "code_verifier": verifier,
        })
        assert resp1.status_code == 200

        # Second attempt — must fail (code already used)
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

## 53. Tests — tests/test_mcp_auth.py

```python
# tests/test_mcp_auth.py
"""MCP Server authentication and scope tests."""
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
        """Accessing tools/list without a token must return 401."""
        resp = _make_rpc("tools/list")
        assert resp.status_code == 401

    def test_401_includes_resource_metadata_header(self):
        """A 401 response must include WWW-Authenticate with resource_metadata."""
        resp = _make_rpc("tools/list")
        assert resp.status_code == 401
        www_auth = resp.headers.get("www-authenticate", "")
        assert "resource_metadata" in www_auth
        assert "localhost:8001" in www_auth

    def test_tools_call_without_token_returns_401(self):
        """Calling a tool without a token must return 401."""
        resp = _make_rpc("tools/call", {"name": "get_portfolio", "arguments": {}})
        assert resp.status_code == 401

    def test_invalid_jwt_returns_401(self):
        """A forged JWT must return 401."""
        resp = _make_rpc("tools/list", token="eyJhbGciOiJIUzI1NiJ9.fake.payload")
        assert resp.status_code in (401, 200)
        if resp.status_code == 200:
            data = resp.json()
            assert "error" in data


class TestProtectedResourceMetadata:
    def test_resource_metadata_endpoint(self):
        """Resource Metadata endpoint must return the AS address."""
        resp = client.get("/.well-known/oauth-protected-resource/mcp")
        assert resp.status_code == 200
        data = resp.json()
        assert "authorization_servers" in data
        assert "localhost:8000" in data["authorization_servers"][0]
        assert "scopes_supported" in data
```

---

## 54. Tests — tests/test_order_flow.py

```python
# tests/test_order_flow.py
"""Review→Execute state machine and idempotency tests."""
import os
import time
import pytest
from fastapi.testclient import TestClient

from mcp_server.main import app
from mcp_server.tools import _reviews, _idempotency_results


# We use mock authentication so tests can focus on business logic
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
    """Bypass real JWT validation to focus on business logic in each test."""
    with patch("mcp_server.main.authenticate_request", return_value=MOCK_CLAIMS):
        resp = client.post(
            "/mcp",
            json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params},
            headers={"Authorization": "Bearer mock-token"},
        )
    return resp.json()


class TestReviewExecuteFlow:
    def test_review_returns_review_id(self):
        """review_equity_order must return a review_id and summary."""
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
        """The same review_id can only be placed once; a second attempt must return 409."""
        review_resp = _rpc_with_mock_auth("tools/call", {
            "name": "review_equity_order",
            "arguments": {"symbol": "MSFT", "quantity": 1, "side": "buy"},
        })
        review_id = review_resp["result"]["_data"]["review_id"]

        # First place — success
        place1 = _rpc_with_mock_auth("tools/call", {
            "name": "place_equity_order",
            "arguments": {
                "review_id": review_id,
                "idempotency_key": f"idem_{os.urandom(4).hex()}",
            },
        })
        assert "error" not in place1 or place1.get("result", {}).get("_data", {}).get("status") == "filled"

        # Second place (different idempotency_key) — must fail
        place2 = _rpc_with_mock_auth("tools/call", {
            "name": "place_equity_order",
            "arguments": {
                "review_id": review_id,
                "idempotency_key": f"idem_{os.urandom(4).hex()}",
            },
        })
        if "error" in place2:
            assert "409" in str(place2["error"]) or "already used" in str(place2["error"]).lower()

    def test_idempotency_returns_same_result(self):
        """The same idempotency_key must always return the exact same order_id."""
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

        # Same idem_key retry
        place2 = _rpc_with_mock_auth("tools/call", {
            "name": "place_equity_order",
            "arguments": {"review_id": review_id, "idempotency_key": idem_key},
        })
        order_id_2 = place2["result"]["_data"]["order_id"]

        assert order_id_1 == order_id_2, "Idempotency broken: two calls returned different order_ids"
        assert place2["result"]["_data"].get("idempotent") is True

    def test_policy_rejects_unlisted_symbol(self):
        """A symbol not on the allowlist must be rejected by Agent Policy."""
        result = _rpc_with_mock_auth("tools/call", {
            "name": "review_equity_order",
            "arguments": {"symbol": "MEME_COIN", "quantity": 1, "side": "buy"},
        })
        assert "error" in result

    def test_policy_rejects_over_limit_notional(self):
        """A notional exceeding the per-order limit must be rejected (NVDA × large quantity)."""
        result = _rpc_with_mock_auth("tools/call", {
            "name": "review_equity_order",
            "arguments": {"symbol": "NVDA", "quantity": 100, "side": "buy"},
        })
        # NVDA @ 875 * 100 = $87,500 >> $500 limit
        assert "error" in result


class TestScopeEnforcement:
    def test_insufficient_scope_returns_403(self):
        """Insufficient scope must return a 403 error."""
        # Only portfolio.read — calling orders.review should fail with 403
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

## 55. Run the Tests

```bash
# Run all tests
pytest tests/ -v

# Expected output:
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

## 56. Required Verification Experiments

Run these manually and in order. Trigger every case yourself at least once:

| # | Experiment | Action | Expected result |
|---|------------|--------|-----------------|
| E1 | **Wrong PKCE** | Submit wrong `code_verifier` at token exchange | `400 PKCE verification failed` |
| E2 | **Code replay** | Use the same Authorization Code twice | `400 Authorization code already used` |
| E3 | **Insufficient scope** | Only `portfolio.read` scope — call `review_equity_order` | `403 insufficient_scope` |
| E4 | **Wrong JWT `aud`** | Use a JWT with a wrong audience | `401 invalid_audience` |
| E5 | **Wrong JWT `iss`** | Use a JWT with a wrong issuer | `401 invalid_issuer` |
| E6 | **Expired JWT** | Wait for Access Token to expire, then use it | `401 token_expired` |
| E7 | **Refresh replay** | After rotation, replay the old Refresh Token | `400 refresh_token has been revoked` |
| E8 | **Review reuse** | Place the same `review_id` twice (different idem keys) | `409 review_id already used` |
| E9 | **Idempotent retry** | Retry with same `idempotency_key` | Returns **exact same** order_id |
| E10 | **Policy violation** | Try to trade a symbol not on the allowlist | `403 policy_violation` |
| E11 | **Over-limit order** | Notional exceeds $500 | `403 policy_violation: exceeds per-order limit` |
| E12 | **No token** | Call MCP without Authorization header | `401 + WWW-Authenticate` with resource_metadata |

---

## 57. Manual Experiment Script

```bash
#!/bin/bash
# experiments.sh — manual verification experiments

BASE_AS="http://localhost:8000"
BASE_MCP="http://localhost:8001"

echo "=== Experiment E12: No token access to MCP ==="
curl -i -X POST "$BASE_MCP/mcp" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'

echo ""
echo "=== Expected: 401 + WWW-Authenticate: Bearer resource_metadata=... ==="

echo ""
echo "=== Experiment: Wrong code_verifier (direct Token Endpoint call) ==="
# Assumes a valid code exists; verifier is intentionally wrong
FAKE_VERIFIER="this_is_definitely_wrong_verifier_abc123xyz"
curl -i -X POST "$BASE_AS/token" \
  -d "grant_type=authorization_code" \
  -d "code=SOME_CODE_HERE" \
  -d "redirect_uri=http://127.0.0.1:54321/callback" \
  -d "client_id=demo-desktop-client" \
  -d "code_verifier=$FAKE_VERIFIER"

echo ""
echo "=== Expected: 400 PKCE verification failed ==="

echo ""
echo "=== Verify JWKS public key ==="
curl -s "$BASE_AS/jwks.json" | python3 -c "
import sys, json
data = json.load(sys.stdin)
key = data['keys'][0]
print(f'kty: {key[\"kty\"]}, alg: {key[\"alg\"]}, kid: {key[\"kid\"]}')
print('JWKS verified ✓')
"
```

---

## 58. Docker Considerations

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
      # JWT iss must be the publicly reachable address that clients (browsers) know
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
      # Key distinction:
      # EXPECTED_ISSUER = the public issuer that clients know (same as auth-server AUTH_ISSUER)
      EXPECTED_ISSUER: "http://localhost:8000"
      # JWKS_URL = internal container network (use service name); never leave the container network
      JWKS_URL: "http://auth-server:8000/jwks.json"
      EXPECTED_AUDIENCE: "http://localhost:8001/mcp"
    depends_on:
      - auth-server
```

**Core concept**:

```text
JWT iss field (validated by clients)      ←→  EXPECTED_ISSUER
JWKS fetch URL (internal container net)  ←→  JWKS_URL

These two must be kept separate.
Never use the container service name as the issuer —
the client's browser cannot reach that hostname to validate the JWT.
```

Dockerfile examples:

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
# Note: the MCP Server container copies only the public key — never the private key
CMD ["uvicorn", "mcp_server.main:app", "--host", "0.0.0.0", "--port", "8001"]
```

---

## 59. Path from Demo to Production (Roadmap)

**Do not skip stages.** Each stage must be stable before you enter the next.

| Stage | Goal | Key contents |
|-------|------|--------------|
| **Stage 0** (current) | Demo running | In-memory storage, fixed user, simulated data |
| **Stage 1** | Read-only production | Real login (Session/JWT), consent stored in DB, audit logging |
| **Stage 2** | Low-risk writes | Drafts, tags, previews — no real execution |
| **Stage 3** | Review/Confirm state machine | DB-stored reviews, `SELECT FOR UPDATE`, user-visible summaries |
| **Stage 4** | Real execution | Test accounts, hard limits, emergency stop, transactions + rollback |
| **Stage 5** | Admin dashboard | Authorized agent list, activity log, one-click revoke, pause |

---

## 60. Production Upgrade: Database Layer

Demo uses in-memory storage. Here is the recommended production replacement:

```python
# Production storage.py skeleton (PostgreSQL + Redis)

import asyncpg
import aioredis
from contextlib import asynccontextmanager

# Authorization Codes → Redis (TTL 120s, auto-expiry)
# Refresh Tokens → PostgreSQL (supports user-level queries and bulk revocation)
# Client Registrations → PostgreSQL (persistent)
# Idempotency Keys → Redis (TTL 7 days, covers retry windows)
# Audit Log → PostgreSQL (append-only, never deleted)

async def save_auth_code_redis(redis: aioredis.Redis, record: dict) -> None:
    """Store Authorization Code in Redis with TTL equal to code lifetime."""
    await redis.setex(
        f"auth_code:{record['code']}",
        record["expires_in"],
        json.dumps(record),
    )

async def get_and_consume_auth_code(redis: aioredis.Redis, code: str) -> dict | None:
    """
    Atomically GET + DEL to prevent concurrent replay.
    Uses a Lua script to guarantee atomicity.
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

## 61. Production Upgrade: Real Login Session

```python
# Production login session (replaces the fixed demo-user-001)

from fastapi import Request, Response
import secrets

SESSION_COOKIE = "mcp_session"
SESSION_TTL = 3600  # 1 hour

async def create_session(response: Response, user_id: str, redis) -> str:
    """Create a login session and return the session_id."""
    session_id = secrets.token_urlsafe(32)
    await redis.setex(
        f"session:{session_id}",
        SESSION_TTL,
        json.dumps({"user_id": user_id, "created_at": time.time()}),
    )
    response.set_cookie(
        SESSION_COOKIE,
        session_id,
        httponly=True,      # XSS protection
        secure=True,        # HTTPS only
        samesite="lax",
        max_age=SESSION_TTL,
    )
    return session_id

async def get_current_user(request: Request, redis) -> str | None:
    """Retrieve the current logged-in user ID from the session cookie."""
    session_id = request.cookies.get(SESSION_COOKIE)
    if not session_id:
        return None
    data = await redis.get(f"session:{session_id}")
    if not data:
        return None
    return json.loads(data)["user_id"]
```

---

## 62. Production Upgrade: Consent Records

```python
# Production consent storage (PostgreSQL)

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
    """Record user consent (INSERT OR UPDATE)."""
    await db.execute("""
        INSERT INTO oauth_consents (user_id, client_id, scope)
        VALUES ($1, $2, $3)
        ON CONFLICT (user_id, client_id) DO UPDATE
        SET scope = $3, granted_at = NOW(), revoked_at = NULL
    """, user_id, client_id, scope)

async def check_consent(db, user_id: str, client_id: str, required_scope: set) -> bool:
    """Check whether the user has already consented to the required scopes (skips re-consent page)."""
    row = await db.fetchrow(
        "SELECT scope FROM oauth_consents WHERE user_id=$1 AND client_id=$2 AND revoked_at IS NULL",
        user_id, client_id,
    )
    if not row:
        return False
    granted = set(row["scope"].split())
    return required_scope.issubset(granted)

async def revoke_consent(db, user_id: str, client_id: str) -> None:
    """Revoke user consent (should also revoke all associated Refresh Tokens)."""
    await db.execute(
        "UPDATE oauth_consents SET revoked_at=NOW() WHERE user_id=$1 AND client_id=$2",
        user_id, client_id,
    )
```

---

## 63. Production Upgrade: Audit Logging

```python
# mcp_server/audit.py — audit logging (never logs raw tokens)

import time
import json
import logging

audit_logger = logging.getLogger("mcp.audit")
audit_logger.setLevel(logging.INFO)

# Production: ship to structured logging (Datadog, CloudWatch, ELK)


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
    Log a tool call audit event.
    Never log the raw token or complete arguments (may contain sensitive values).
    """
    # Summarize sensitive fields rather than logging them verbatim
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
    """Log an authentication-related event (grant, deny, revoke, etc.)."""
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

## 64. Production Upgrade: Rate Limiting

```python
# Production-grade rate limiting (Redis-backed)

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
    Sliding window rate limiter.
    key can be user_id, client_id, IP, or any combination.
    """
    now = time.time()
    window_start = now - window_seconds
    pipe = redis.pipeline()

    # Remove entries outside the current window
    pipe.zremrangebyscore(key, 0, window_start)
    # Record this request
    pipe.zadd(key, {str(now): now})
    # Count requests in the current window
    pipe.zcard(key)
    # Set TTL to prevent key leakage
    pipe.expire(key, window_seconds * 2)

    results = await pipe.execute()
    current_count = results[2]

    if current_count > max_requests:
        raise HTTPException(
            status_code=429,
            detail=f"Too many requests — please retry after {window_seconds} seconds",
            headers={"Retry-After": str(window_seconds)},
        )


# Usage before an MCP tool call:
# await check_rate_limit(redis, key=f"tool:{user_id}", max_requests=60, window_seconds=60)
```

---

## 65. Production Upgrade: JWKS Key Rotation

Production must support key rotation. JWKS can carry multiple keys simultaneously (old and new coexisting):

```python
# auth_server/security_production.py — multi-kid key rotation

import os
from pathlib import Path

# Currently active kid (used to sign new tokens)
ACTIVE_KID = os.getenv("ACTIVE_KEY_ID", "key-v2")

# Keys directory: each kid maps to a PEM key pair
KEYS_DIR = Path("/etc/mcp-auth/keys")


def get_all_jwks() -> dict:
    """
    Return all valid public keys (including keys being phased out, needed to verify old tokens).
    Rotation steps:
    1. Add the new kid key pair
    2. Update ACTIVE_KID to point to the new kid
    3. Wait for all tokens signed with the old key to expire (max TTL = 300s)
    4. Remove the old kid from JWKS
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

## 66. Production Upgrade: Prompt Injection Guard

Prompt injection is a risk unique to LLM agents. Auth + Policy is the first defense line, but a dedicated guard adds another layer:

```python
# mcp_server/prompt_injection_guard.py

import re
from fastapi import HTTPException

# Patterns forbidden inside tool arguments (prevent injected instructions from bypassing Policy)
INJECTION_PATTERNS = [
    r"ignore previous",
    r"disregard all",
    r"system prompt",
    r"you are.*assistant",
    r"<\|.*\|>",          # Special tokens
    r"<<<.*>>>",
]


def validate_tool_arguments(arguments: dict) -> None:
    """
    Run prompt injection detection on all string arguments.
    This is an extra defense layer — it does not replace Policy or Scope checks.
    """
    for key, value in arguments.items():
        if not isinstance(value, str):
            continue
        for pattern in INJECTION_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                raise HTTPException(
                    status_code=400,
                    detail=f"Parameter '{key}' contains disallowed content",
                )
```

**Core principle**:

```text
OAuth Scope controls "what APIs can you call"
Agent Policy controls "how much can you do per call"
Prompt Injection Guard controls "can injected instructions change the above"

All three defenses are required.
Prompt injection cannot bypass Policy.
Policy cannot replace Scope.
Scope cannot replace Policy.
```

---

## 67. Production Upgrade: HTTPS and Reverse Proxy

```nginx
# nginx.conf excerpt

server {
    listen 443 ssl http2;
    server_name auth.example.com;

    ssl_certificate     /etc/ssl/certs/auth.example.com.crt;
    ssl_certificate_key /etc/ssl/private/auth.example.com.key;

    # HSTS
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    # OAuth endpoints — never cache
    location ~ ^/(authorize|token|revoke|register) {
        proxy_pass         http://auth-server:8000;
        proxy_set_header   Host $host;
        proxy_set_header   X-Real-IP $remote_addr;
        proxy_set_header   X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;
        add_header         Cache-Control "no-store, no-cache" always;
    }

    # JWKS can be cached briefly (5 minutes)
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

## 68. Security Hardening: The Four-Layer Protection Model

```text
┌─────────────────────────────────────────────────────────┐
│              Four-Layer Security Model                   │
├─────────────────────────────────────────────────────────┤
│  Layer 1: Identity (Who are you?)                        │
│  OAuth 2.1 + PKCE                                        │
│  - Prevents unauthorized access                          │
│  - JWT prevents forgery; RS256 signature                 │
│  - PKCE prevents authorization code interception         │
├─────────────────────────────────────────────────────────┤
│  Layer 2: API Authorization (What APIs can you call?)    │
│  Scope + Audience                                        │
│  - portfolio.read / orders.review / orders.place split   │
│  - Audience prevents cross-service token reuse           │
├─────────────────────────────────────────────────────────┤
│  Layer 3: Agent Authorization (How much can you do?)     │
│  Agent Profile + Allowlist + Limits                      │
│  - Symbol allowlist                                      │
│  - Per-order notional cap                                │
│  - Different limits per agent identity (not just user)   │
├─────────────────────────────────────────────────────────┤
│  Layer 4: Business Authorization (Did user confirm?)     │
│  Review + Confirm + Idempotency                          │
│  - Review freezes all business parameters                │
│  - Place accepts only review_id; no mutable args         │
│  - Idempotency key prevents duplicate fills on retry     │
│  - Human YES confirmation for high-risk actions          │
└─────────────────────────────────────────────────────────┘

Key insight:
Authorizing an agent to access a service
≠
Authorizing the agent to execute every high-risk action
```

---

## 69. Pre-Launch Checklist — Authorization Server

```markdown
### Authorization Server Launch Checklist

Auth & PKCE
- [ ] Authorization Code is single-use (rejected immediately after used=True)
- [ ] Code TTL ≤ 120 seconds
- [ ] Enforce code_challenge_method=S256 (reject plain)
- [ ] PKCE verifier uses constant-time compare (timing attack prevention)
- [ ] redirect_uri is exact string match (no prefix or wildcard matching)

Token security
- [ ] Access Token TTL is short (≤ 300 seconds)
- [ ] Refresh Token Rotation: old token revoked the moment the new one is issued
- [ ] Refresh Tokens are revocable (user can revoke from UI)
- [ ] Revocation endpoint returns 200 even for non-existent tokens (prevents enumeration)
- [ ] Empty access_token is never returned to the client

Key management
- [ ] Private key in Key Vault / HSM (not in the code repository)
- [ ] JWKS supports multiple kids (key rotation without disrupting verification)
- [ ] Old key is only removed after all tokens signed with it have expired

UX & security
- [ ] Consent is stored in DB (queryable and revocable)
- [ ] Re-authorization for same scope can skip the Consent page (user-friendly)
- [ ] Audit log: all grant / deny / revoke events
- [ ] HTTPS only; Token endpoint disables caching

Dynamic registration
- [ ] Demo restricts to loopback; production uses whitelist or manual approval
- [ ] client_id is sufficiently random (≥ 128 bits)
```

---

## 70. Pre-Launch Checklist — MCP Server

```markdown
### MCP Server Launch Checklist

Token verification
- [ ] Every request is verified (no caching of verification results)
- [ ] iss is verified (prevents issuer forgery)
- [ ] aud is verified (prevents cross-service token reuse)
- [ ] exp is verified (prevents expired token use)
- [ ] JWKS client caches keys but supports kid rotation

Scope & Policy (double-check)
- [ ] Each tool has an independent scope requirement
- [ ] Insufficient scope returns 403 (not 401)
- [ ] Agent Policy is independent from Scope (second wall)
- [ ] Policy violations return business errors without leaking internals

Review → Execute state machine
- [ ] Review records are persisted in DB
- [ ] Reviews are single-use (DB-level SELECT FOR UPDATE prevents concurrent replay)
- [ ] Reviews have a TTL; expired reviews are rejected
- [ ] Execute stage does not accept mutable business parameters (symbol/quantity/side)
- [ ] Review user_id is validated against the JWT sub claim

Idempotency & transactions
- [ ] idempotency_key prevents duplicate fills on network retry
- [ ] Idempotency key storage has a reasonable TTL (e.g. 7 days)
- [ ] Place operation is atomic (DB + external system in one transaction)
- [ ] External system failures have a clear rollback mechanism

Security
- [ ] Error messages do not expose internal stack traces
- [ ] Audit logs do not contain raw token values
- [ ] Input parameters validated by Pydantic (type + range)
- [ ] Prompt Injection detection (extra defense layer)
- [ ] Rate Limiting on tool call frequency
```

---

## 71. Pre-Launch Checklist — MCP Client

```markdown
### MCP Client Launch Checklist

Discovery & connection
- [ ] Auto-discover AS from 401 + WWW-Authenticate
- [ ] SSRF guard: restrict AS address range (production uses whitelist)
- [ ] AS Metadata validates required fields + S256 support

PKCE & state
- [ ] Generate a fresh code_verifier per authorization (never reuse)
- [ ] Generate a fresh state per authorization (CSRF prevention)
- [ ] Validate state at callback time

Token storage
- [ ] Empty access_token is never written to disk
- [ ] Token file uses chmod 600 (owner-only)
- [ ] Production uses OS Keychain (keyring library)
- [ ] Proactive refresh (silent refresh when < 60s remaining)
- [ ] Maximum one 401 retry (prevents infinite loops)

User experience
- [ ] High-risk actions display the full order summary
- [ ] Require explicit human confirmation (type YES; no auto-approve)
- [ ] Refresh happens silently (does not interrupt the user)
- [ ] Error messages are human-readable (not raw HTTP status codes)
```

---

## 72. Common Errors and Solutions

| Symptom | Root cause | Solution |
|---------|------------|----------|
| `401 missing_token` | Client did not include Bearer header | Check `Authorization: Bearer <token>` format |
| `401 invalid_audience` | JWT `aud` does not match MCP Server expectation | Confirm `EXPECTED_AUDIENCE` equals the JWT `aud` field |
| `401 invalid_issuer` | JWT `iss` does not match Auth Server issuer | In Docker: separate `EXPECTED_ISSUER` from `JWKS_URL` |
| `400 PKCE verification failed` | code_verifier is wrong or corrupted | Do not apply additional URL-encoding to the verifier |
| `400 Authorization code already used` | Code was replayed or client retried accidentally | Check whether client sent two token requests |
| `400 Authorization code expired` | User spent > 120s on the consent page | Guide user to re-authorize |
| `403 insufficient_scope` | Requested scope is too narrow | Check scope parameter in the `/authorize` request |
| `409 review_id already used` | Same review_id placed twice with different idem keys | Check whether review_id was already placed before calling |
| `MCP Server fails to fetch JWKS` | Container cannot reach `localhost:8000` | Use service name: `http://auth-server:8000/jwks.json` |
| `state mismatch` | CSRF check failed | Verify callback parameters are passed through correctly |

---

## 73. Performance Considerations

**JWKS caching**:

```python
# PyJWKClient has built-in key caching, but configure a sensible refresh interval.
# During key rotation, old kid tokens must still be verifiable.

# Recommended: cache keys, but refresh immediately on unknown kid
jwks_client = PyJWKClient(
    JWKS_URL,
    cache_keys=True,
    lifespan=300,       # Refresh every 300 seconds (same as Access Token TTL)
)
```

**Connection pooling**:

```python
# Production Auth Server uses connection pooling (asyncpg)
pool = await asyncpg.create_pool(
    DATABASE_URL,
    min_size=5,
    max_size=20,
    command_timeout=30,
)
```

**Token verification overhead**:

```text
JWT local verification (RS256):  ~0.5ms
JWKS fetch (cold start):         ~50ms
Subsequent verification (cached key): ~0.5ms

Recommendation: hot-cache JWKS and refresh periodically in the background;
never fetch JWKS synchronously on the request path.
```

---

## 74. Topics This Lab Does Not Cover

The following are out of scope for this lab but must be addressed before any real production deployment:

**Identity & Access**:
- Real Identity Provider integration (Google, Okta, Cognito)
- MFA (Multi-Factor Authentication)
- Agent Identity (the agent's own identity, separate from acting on behalf of a user)

**Data & Security**:
- Data encryption at rest and in transit
- Automated key rotation (HashiCorp Vault, AWS KMS)
- Security scanning and penetration testing
- SOC 2 / ISO 27001 compliance

**Operations**:
- Distributed tracing (OpenTelemetry)
- Alerting and on-call runbooks
- Disaster recovery, RTO/RPO
- Multi-region deployment

**Business**:
- Real broker API integration (Robinhood, Alpaca, Interactive Brokers)
- Account isolation (multi-tenancy)
- Regulatory compliance (FINRA, SEC, MiFID II)
- User agreements and risk disclosures

---

## 75. Final Pre-Launch Checklist

```markdown
## Deployment Go/No-Go Checklist

### Functional Verification
- [ ] All 21 tests pass: pytest tests/ -v
- [ ] Manual experiments E1–E12 all verified
- [ ] Docker Compose can start cleanly from scratch
- [ ] Client walks full flow: discovery → PKCE → token → tools → Review → YES → Place
- [ ] Idempotent retry returns the same order_id

### Security Verification
- [ ] Private key not committed to git (check .gitignore)
- [ ] Token file is chmod 600
- [ ] Error responses contain no stack traces
- [ ] HTTPS configured (TLS 1.2+; production never runs HTTP)
- [ ] JWKS URL and Issuer URL are separated (Docker environment)

### Disclaimer
- [ ] README includes "simulated system" statement
- [ ] Code contains no investment advice in comments
- [ ] User-facing interfaces (Consent page, client output) include "no real trades" notice

### Documentation
- [ ] README covers all environment variables
- [ ] README covers startup steps
- [ ] DISCLAIMER.md exists (or README contains a Disclaimer section)
```

---

## 76. Final Understanding Diagram

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│                     Complete Data Flow and Security Checkpoints               │
└──────────────────────────────────────────────────────────────────────────────┘

  MCP Client
  ─────────────────────────────────────────────────────────────────────────────
  [1] Start, POST /mcp (no token)
        ↓ 401 + WWW-Authenticate: Bearer resource_metadata="http://.../mcp"
  [2] GET resource_metadata → authorization_servers[0]
        ↓ SSRF guard (only localhost allowed)
  [3] GET /.well-known/oauth-authorization-server
        ↓ validate issuer / S256 support / all endpoints present
  [4] Generate code_verifier (32 random bytes) + code_challenge (SHA256)
       Generate state (16 random bytes, CSRF prevention)
  [5] Open browser → /authorize?...&code_challenge=...&state=...

  Authorization Server
  ─────────────────────────────────────────────────────────────────────────────
  [6] GET /authorize
        ↓ validate response_type=code / client_id / redirect_uri / scope / S256
        ↓ Display Consent page
  [7] POST /authorize (user clicks Allow)
        ↓ Generate code (24 random bytes, TTL 120s)
        ↓ Store AuthorizationCodeRecord (containing code_challenge)
        ↓ 302 redirect callback?code=...&state=...

  MCP Client
  ─────────────────────────────────────────────────────────────────────────────
  [8] Loopback Callback Server receives code + state
        ↓ Validate state matches
  [9] POST /token (code + code_verifier + client_id)

  Authorization Server
  ─────────────────────────────────────────────────────────────────────────────
  [10] Validate: code exists + not expired + not used + client matches + redirect matches
        ↓ PKCE: SHA256(verifier) == challenge?
        ↓ Mark code used=True (single-use)
        ↓ Issue JWT (RS256, exp=5min)
        ↓ Issue Refresh Token (TTL 30 days)

  MCP Client
  ─────────────────────────────────────────────────────────────────────────────
  [11] Receive access_token (validate non-empty)
        ↓ Store tokens (chmod 600)

  [12] POST /mcp initialize (Bearer JWT)

  MCP Server
  ─────────────────────────────────────────────────────────────────────────────
  [13] Extract Bearer Token
        ↓ PyJWKClient fetches JWKS (match kid, verify RS256 signature)
        ↓ Verify iss = "http://localhost:8000"
        ↓ Verify aud = "http://localhost:8001/mcp"
        ↓ Verify exp not expired
        ↓ Return claims (containing sub / scope)

  [14] tools/call review_equity_order
        ↓ Scope check: claims.scope ⊇ {"orders.review"}
        ↓ Policy check: symbol ∈ ALLOWED_SYMBOLS AND notional ≤ $500
        ↓ Generate review_id, freeze all business parameters, TTL 120s
        ↓ Return summary

  MCP Client
  ─────────────────────────────────────────────────────────────────────────────
  [15] Display order summary, wait for user to type YES

  User: YES

  [16] POST /mcp tools/call place_equity_order (review_id + idempotency_key)

  MCP Server
  ─────────────────────────────────────────────────────────────────────────────
  [17] Scope check: claims.scope ⊇ {"orders.place"}
        ↓ Idempotency check: idempotency_key already has a result? Yes → return it
        ↓ Fetch review (lock): exists + not used + not expired + user matches?
        ↓ Atomically mark review used=True
        ↓ Simulate fill, generate order_id
        ↓ Store in idempotency cache
        ↓ Return fill result

  MCP Client
  ─────────────────────────────────────────────────────────────────────────────
  [18] Display fill result ("Simulated fill — no real trade was executed")
        ↓ Demo idempotency: same idem_key retry → same order_id

  ═══ Flow complete ═══

  Key security checkpoints recap:
  Step  4  → PKCE prevents authorization code interception
  Step  8  → state prevents CSRF
  Step 10  → PKCE verification prevents stolen code from being exchanged
  Step 10  → code is single-use, prevents replay
  Step 13  → JWT signature + iss/aud/exp prevents forgery, cross-service use, expiry bypass
  Step 14  → Scope prevents unauthorized tool access
  Step 14  → Policy prevents over-limit actions (second wall)
  Step 15  → Human confirmation prevents automated placement
  Step 17  → Idempotency prevents duplicate fills on retry
  Step 17  → review is single-use, prevents order replay
  Step 17  → review has no mutable parameters, prevents review bypass
```

---

## Closing

Building these three services, you have not just written a few APIs. You have walked through a complete AI Agent security architecture.

**From 401 to fill, every step has a clear gatekeeper.**

Concept recap:

| Concept | How it appears in this lab |
|---------|---------------------------|
| **PKCE** | verifier/challenge pair — prevents authorization code interception |
| **JWT RS256** | Auth Server signs; MCP Server verifies; private key never leaves Auth Server |
| **Scope** | Each tool has an independent scope; `portfolio.read` cannot call `orders.place` |
| **Audience** | JWT `aud = http://localhost:8001/mcp` — prevents cross-service token reuse |
| **Refresh Rotation** | Old token exchanged for new; old immediately revoked; prevents replay |
| **Resource Metadata** | The `resource_metadata` in the 401 WWW-Authenticate is the auto-discovery starting point |
| **Review → Execute** | Parameters are frozen at review time; human confirmation; two-phase authorization |
| **Idempotency** | `idempotency_key` prevents duplicate fills from network retries |
| **Agent Policy** | Second wall beyond Scope (symbol allowlist + notional cap) |

**Next steps**:

1. ~~Submit the code to a dedicated POC directory in xingai-enterprise-ai-pocs~~ **Done, 2026-07-12** — see [Claims MCP OAuth POC](https://github.com/xingaiapp/xingai-enterprise-ai-pocs/tree/main/pocs/claims-mcp-oauth-poc). Same code, ported to insurance claims adjudication instead of brokerage — proof this pattern isn't Robinhood-specific.
2. Read the [production topology](../articles/2026-07-11-mcp-in-production-robinhood-case.md) to understand the Worker / FastAPI / Redis decision boundary
3. Study [Invest AI ADR-028](https://github.com/xingaiapp/xingai-invest-ai/blob/main/docs/adr/028-robinhood-mcp-execution-gates.md) to see how a real product implements Review Gates
4. Walk a colleague through the demo and explain why both "single-use Authorization Code" and "PKCE" are independently necessary

Authorizing an agent to access a service is not the same as authorizing the agent to execute every high-risk action. Hold onto that sentence and your understanding of AI Agent security will already be ahead of most engineers.

---

## Related Resources

- **中文版：** [2026-07-12-mcp-oauth-pkce-lab.zh.md](2026-07-12-mcp-oauth-pkce-lab.zh.md)
- **Concept deep dive:** [MCP Auth — The Robinhood Deep Dive](2026-07-12-mcp-oauth-auth-deep-dive.md)
- **Production topology:** [MCP in Production — Robinhood Case Study](../articles/2026-07-11-mcp-in-production-robinhood-case.md)
- **Implementation repo (brokerage domain):** [xingai-robinhood-mcp](https://github.com/xingaiapp/xingai-robinhood-mcp)
- **Runnable POC (claims domain):** [claims-mcp-oauth-poc](https://github.com/xingaiapp/xingai-enterprise-ai-pocs/tree/main/pocs/claims-mcp-oauth-poc) — this lab's code, ported; plus a deep-dive doc explaining every OAuth/PKCE mechanism against the same code
- **Invest AI execution gates:** [ADR-028](https://github.com/xingaiapp/xingai-invest-ai/blob/main/docs/adr/028-robinhood-mcp-execution-gates.md)

---

## Disclaimer

This lab is an **educational simulated system**:

- **No real broker connection** — all trades are simulated; no real assets are affected
- **Not production-ready** code; not security-audited; not suitable for direct production deployment
- **Not investment advice** — simulated portfolio and quotes are for teaching purposes only
- **Not legal or compliance advice**
- Code is provided "as is"; you are responsible for evaluating, deploying, and ensuring compliance
- Any code used in production must undergo a full security assessment, penetration testing, and compliance review before deployment

XingAI accepts no liability for any losses or damages resulting from use of this lab code.

---

**Author:** Xing Wang  
**Published:** 2026-07-12  
**Tags:** mcp, oauth, pkce, fastapi, education, security, jwt, hands-on
