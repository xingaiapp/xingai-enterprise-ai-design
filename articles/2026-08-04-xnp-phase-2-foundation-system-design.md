---
title: XNP Phase 2 Foundation — Modular Monolith That Boots Empty
author: Xing Wang
date: 2026-08-04
tags: [architecture, xnp, notifications, modular-monolith, postgres, outbox, design-patterns]
description: Phase 2 of XingAI Notification Platform ships API + Worker + Postgres outbox + JWT tenancy with no channel providers — scaffolding you refuse to skip.
---

# XNP Phase 2 Foundation: Modular Monolith That Boots Empty

> *When do you wire Twilio — after the host can reject a bad JWT, or before?*

**Short answer:** After. Phase 2 of XNP is a modular monolith that builds, health-checks Postgres, enforces JWT tenant scope, and dispatches outbox rows in-process — with **no** SMS/email/push providers. Channel vertical slices start in Phase 3+.

![XNP Phase 2 Foundation — System Design UX](../assets/xnp-phase-2-foundation-system-design-ux.png)

---

## 5W Framework

### What

| Component | Role |
|---|---|
| `Xnp.Api` | ASP.NET Core host, JWT, tenant middleware, health, OTel |
| `Xnp.Worker` | Outbox dispatcher (single writer) |
| `Xnp.SharedKernel` | Domain primitives, `IMessageBus`, outbox/inbox models |
| `Xnp.Infrastructure` | EF Core + Postgres entity configs |
| Docker Compose | Postgres 16; optional full API profile |

Phase 1 already accepted ADRs 0001–0018 (modular monolith, Postgres, Service Bus-for-prod, tenancy, idempotency, etc.). Phase 2 **implements** the skeleton those ADRs imply.

### Who

- Platform architects owning cross-product notifications
- .NET engineers bootstrapping the repo
- Product leads asking for "just one SMS" too early
- Security reviewers checking multi-tenant JWT refusal

### Why

Without Phase 2:

- Apps keep calling Twilio/SendGrid directly (explicit non-goal of XNP)
- Half-wired providers hide missing tenancy / outbox / audit

With Phase 2:

- One bootable boundary for future vertical slices
- Unsigned JWT fails; ready probe reflects DB
- In-process outbox today mirrors contracts Service Bus will use later

### When

| Stage | Need |
|---|---|
| Phase 1 | Architecture package (done) |
| Phase 2 | Skeleton (done) |
| Phase 3 | Identity / contacts / consent |
| Phase 4+ | SMS slice → email/push → schedules → campaigns |

**Rule:** One vertical slice before horizontal fan-out.

### Where

```text
XingAI apps ──(future REST/events)──► Xnp.Api
                                         │
                                    EF / Postgres
                                         │
                                    outbox_message
                                         │
                                      Xnp.Worker → IMessageBus (in-memory now)
```

---

## Anti-patterns

- Shipping Twilio before JWT tenant middleware
- Calling Phase 2 "production notification platform"
- Skipping outbox because "we'll add it later"
- Letting apps keep dual-writing providers "temporarily"

---

## Related

- `docs/architecture/system-design.md` (+ `.zh.md`)
- ADR-0019 / ADR-0020
- Tech blog: `2026-08-04-xnp-phase-2-foundation-modular-monolith.md`
