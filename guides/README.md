# Education Guides

Step-by-step learning tracks that sit beside the architecture articles. Same bilingual rule: English (`.md`) + 中文 (`.zh.md`).

For the complete beginner-to-CTO sequence, start with the [XingAI AI Engineering Learning Series](../courses/README.md) · [中文](../courses/README.zh.md). The guides below are deeper companion labs referenced by the curriculum.

Architecture deep dives stay under [`articles/`](../articles/). These guides teach **industry-standard mechanics** with runnable lab outlines — they are not product marketing and not investment advice.

## Guides

| Date | Title | Audience | Tags |
|------|-------|----------|------|
| 2026-07-12 | [MCP Auth from Robinhood — OAuth 2.1 / PKCE / Token Verification](2026-07-12-mcp-oauth-auth-deep-dive.md) · [中文](2026-07-12-mcp-oauth-auth-deep-dive.zh.md) | Engineers new to MCP auth, platform & security | `mcp` `oauth` `pkce` `jwt` `education` |
| 2026-07-12 | [Build an OAuth 2.1 + PKCE MCP Project from Scratch](2026-07-12-mcp-oauth-pkce-lab.md) · [中文](2026-07-12-mcp-oauth-pkce-lab.zh.md) | Engineers implementing a demo Auth + MCP stack | `mcp` `oauth` `fastapi` `hands-on` `education` |

## Learning path

1. Read the [production Robinhood MCP article](../articles/2026-07-11-mcp-in-production-robinhood-case.md) for topology (Cursor → mcp-remote → vendor).  
2. Read **MCP Auth deep dive** for OAuth / PKCE / JWT / review→execute concepts.  
3. Follow the **PKCE lab** to build Auth Server + MCP Server + Client against a **simulated** portfolio.  
4. Compare with [xingai-robinhood-mcp](https://github.com/xingaiapp/xingai-robinhood-mcp) for fail-closed gateway gates in a real product path.

## Disclaimer

Guides are informational and educational. Lab code is not production-ready. Not investment, legal, or compliance advice.
