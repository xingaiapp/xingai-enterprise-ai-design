---
title: XNP Phase 3+ Next — Phased Roadmap System Design
author: Xing Wang
date: 2026-09-25
tags: [architecture, xnp, notifications, modular-monolith, consent, phased-roadmap]
description: After XNP Phase 2 empty-boot foundation — Phase 3 identity/contacts/consent, then one channel slice before fan-out.
---

# XNP Phase 3+ Next — Phased Roadmap System Design

> *Phase 2 boots with zero channel providers. What ships next without becoming “Twilio with extra steps”?*

**Short answer:** Phase 3 owns **identity, contacts, and consent**. Only then does Phase 4+ add one vertical channel slice (SMS first). Fan-out comes after one slice works end-to-end.

![XNP Phase 3+ Next — Phased Roadmap](../assets/xnp-phase-3-next-phased-roadmap-system-design-ux.png)

---

## 5W Framework

### What

| Stage | Scope |
|---|---|
| Phase 2 (done) | API + Worker + Postgres outbox + JWT tenancy — **no** providers |
| Phase 3 (next) | Identity, Contacts, Consent / preferences |
| Phase 4+ | SMS slice → email/push → schedules → campaigns |
| Prod bus | Azure Service Bus replacing in-process bus when ready |

Builds on ADRs 0001–0020 and the Phase 2 foundation article (2026-08-04).

### Who

- Platform owners of cross-product notifications
- Product teams tempted to “just send one SMS”
- Security reviewing multi-tenant consent

### Why

Skipping Phase 3: apps call providers directly; consent and contact ownership are afterthoughts; outbox exists but has nothing lawful to send.

### When

| Stage | Need |
|---|---|
| MVP (Phase 2) | Empty boot, health, JWT refuse bad tokens |
| POC (Phase 3) | Contact + consent models; enqueue denied without consent |
| Production-shaped | Service Bus, retries/DLQ, encryption secrets |
| Phase 4+ | First SMS provider behind abstraction — then others |

**Rule:** One vertical slice before horizontal fan-out. Providers after consent.

### Where

```text
XingAI apps → Xnp.Api (JWT) → domain modules
                    ↓
              Postgres + outbox
                    ↓
              Worker → IMessageBus → (Phase 4+) channel providers
```

---

## How It Works

### Example: Phase 3 deny without consent

```text
Step 1 · App · POST notification intent · JWT tenant ok
Step 2 · Contacts · resolve destination
Step 3 · Consent · SMS not granted → DENY enqueue
Step 4 · Audit · reason=consent_missing · no provider call · Completed
```

---

## Enterprise Pattern Mapping

| Pattern | Application |
|---|---|
| Modular monolith | Host ready; slices land as modules |
| Outbox | In-process now; Service Bus contract later |
| Phased roadmap | Empty boot → identity/consent → one channel |

---

## Anti-Patterns

| Anti-pattern | Why it fails | Do instead |
|---|---|---|
| Twilio before JWT/consent | Tenancy and law last | Phase 2 then 3 then provider |
| All channels at once | Half-wired chaos | One SMS slice first |
| App→provider direct | XNP non-goal | Always via platform |

---

## POC vs Phase 2+

| Phase 2 validated | Next |
|---|---|
| Boots empty, JWT, outbox | Phase 3 identity/contacts/consent |
| In-process bus | Service Bus for prod |
| No providers | SMS then email/push |

---

## Related Documents

- [XNP Phase 2 Foundation](./2026-08-04-xnp-phase-2-foundation-system-design.md)
- [xingai-notification-platform](https://github.com/xingaiapp/xingai-notification-platform) `docs/PHASE2-CHECKPOINT.md`
- Product mirror: `docs/architecture/xnp-phase-3-next-phased-roadmap.md`
- 中文: [2026-09-25-xnp-phase-3-next-phased-roadmap.zh.md](./2026-09-25-xnp-phase-3-next-phased-roadmap.zh.md)
