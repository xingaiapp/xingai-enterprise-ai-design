# Claims Copilot Agent — Architecture Note

Canonical long-form (EN/zh + poster):

- [EN article](../../articles/2026-09-25-claims-copilot-agent-phased-roadmap.md)
- [中文](../../articles/2026-09-25-claims-copilot-agent-phased-roadmap.zh.md)
- Course: [courses/claims-copilot-agent](../../courses/claims-copilot-agent/README.md)

![Claims Copilot phased roadmap](./claims-copilot-agent-phased-roadmap-system-design-ux.png)

## Phase cheat sheet

| Phase | Ship |
|---|---|
| MVP | Single Agent + mock tools + structured summary |
| POC | MCP stubs + HITL on writes + citations |
| Production-shaped | Entra ID + OBO + audit + golden eval in CI |
| Later | Multi-Agent Review only after eval is green |

**Rule:** Tools and approval before Multi-Agent.
