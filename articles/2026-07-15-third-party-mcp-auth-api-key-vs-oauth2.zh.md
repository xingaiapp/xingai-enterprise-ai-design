---
title: 第三方 MCP 访问——用 API Key 还是 OAuth 2.1?一份决策框架
author: Xing Wang
date: 2026-07-15
tags: [architecture, enterprise, mcp, oauth, api-design, security, third-party-integration, design-patterns]
description: 当第一个外部合作方需要调用 MCP Server 时,团队几乎本能地会先上一个静态 API Key,因为这是最快能上线的方案。本文给出一个具体的判断框架,说明什么时候这样做没问题、什么时候不行,并用 xingai-enterprise-ai-pocs 里三个 POC 的真实演进过程把框架讲透。
---

# 第三方 MCP 访问:用 API Key 还是 OAuth 2.1?一份决策框架

这个问题几乎在 MCP Server 第一次有了"自己进程之外的调用方"那一刻就会出现:这个调用方需要一个静态 API Key,还是需要带 scope、按合作方区分的真实 OAuth 2.1 Token?静态 Key 一个下午就能上线。OAuth 2.1 + PKCE + JWT 需要真功夫——Authorization Server、JWKS 端点、Token 签发与轮换、scope 设计。本能的答案几乎总是"先上 Key,认证以后再说"。有时候这个决定是对的。但很多时候不是,而且做错的代价往往要等到合作方集成已经上线了才会显现。

这不是一个理赔或保险专属的问题,但用一个具体案例讲会更清楚:`xingai-enterprise-ai-pocs` 里有三个 POC 在三个不同的时间点做过同样的决策,它们的演进过程——`claims-mcp-oauth-poc`(从第一天就用真实 OAuth)、`claims-partner-api-mcp-poc`(用静态 Key,并明确标注为缺口)、`claims-workflow-v2-poc`(现在用静态 Key,但 scope 命名已经为未来接 OAuth 预留好)——是一个很有用的实例,贯穿本文始终。

---

## 5W Framework

### What

| | 静态 API Key | OAuth 2.1 + PKCE + JWT(按 scope 分权) |
|---|---|---|
| 粒度 | 全有或全无——一个 Key 能调用 Server 暴露的所有工具 | 按 scope 分(`claims.read`、`payments.write` ……)——可以只给一个合作方签发它需要的那部分权限的 Token |
| 吊销 | 轮换共享密钥——所有合法持有者会被同时切断 | 可以单独吊销或让某个合作方的 Token 过期,不影响其他合作方 |
| 按调用方区分身份 | 没有,除非自己再建一套 Key 到合作方的映射 | 内建——JWT 的 `sub` claim 把每次调用绑定到具体合作方 |
| 可审计性 | "拿着这把 Key 的某个人做了这件事" | "合作方 X,在 T 时刻签发的 Token,scope 是 Y,做了这件事" |
| 实现成本 | 几分钟 | 需要 Authorization Server、JWKS、Token 签发/轮换、scope 设计——几天到几周 |
| 最适合 | 只有内部调用方,即还没有真正跨越信任边界 | 任何来自自己进程之外的调用方,尤其是涉及资金流动或有法律后果的决策 |

### Who

- **企业/AI 架构师**——为一个新的对外 MCP Server 决定认证模式
- **安全评审人员**——在第三方集成上线前评估风险
- **平台工程师**——接手了"先用静态 Key 顶着"的历史决定,需要知道什么时候这个决定就不再站得住了
- **合规/法务相关方**——需要的审计追踪要能绑定到具体的外部调用方,而不只是"某个持有有效凭证的人"

### When

要在第一个外部合作方接入之前定下来,不要等接入之后再定——在已经签发了 N 个静态 Key 之后再补一套带 scope 的 OAuth,不只是工程问题,更是合作方协调问题:每个合作方都需要一个迁移窗口,在所有人都迁移完之前,Server 得同时支持两套认证机制。`claims-partner-api-mcp-poc` 自己的 ADR([ADR-007](https://github.com/xingaiapp/xingai-enterprise-ai-pocs/blob/main/docs/adr/007-claims-partner-api-mcp-poc-full-coverage.zh.md))之所以用静态 Key 作为明确标注的第一阶段缺口,正是因为团队已经知道这笔迁移成本迟早要付,选择先做覆盖面、认证往后放,而不是假装这个缺口不存在。

### Where

适用于任何 MCP(或其他 API)Server 有一个跨出组织自身信任边界的调用方的场景——不限于理赔或保险。同样的取舍在支付类 API、医疗数据 API、HR 系统,或任何"谁做了什么"需要挂上监管审计要求的领域里都会重演。

### Why

因为这两种方案失败的方式不一样,而且都不会大声地失败:

- **静态 Key 的失败方式是悄无声息的过度授权。** 一个被授予"这个 Server 能做的一切"权限的 Key,不会主动告诉你它权限过大——它就那么放着,能力远超任何单个合作方集成实际需要的范围,直到一次泄露或者一个被攻破的合作方系统把这个未被使用的能力变成一次真实事故。失败在发生之前是看不见的。
- **没有第二层授权的 OAuth,失败方式是把 scope 误当成业务限额。** 一个 `claims.adjudicate` scope 回答的是"这个 Token 到底能不能裁决理赔"——它完全没有回答"用这个 Token 裁决一笔 50 万美元的赔付该不该放行"。只看 scope,会一直显得"已经充分授权",直到有人问出一个本该由业务规则检查拦下来的问题。

---

## 一份决策框架

**同时满足**以下条件时,用静态 Key:

- 调用方在你自己的进程或自己的基础设施内部——还没有真正跨越外部信任边界
- 只有一个调用方,所以"这是哪个合作方做的"这个概念本身就没有意义
- Server 暴露的东西不涉及资金移动,也不产生有法律后果的决定(拒赔、不利行动、监管报送)
- 你有一个明确、被追踪记录的计划,说明在第二个调用方(尤其是外部的)接入之前该用什么取代这把 Key——而不是"到时候再说"

**只要满足以下任意一条**,就该换成按工具分 scope 的 OAuth 2.1 + PKCE + JWT:

- 有一个来自自己基础设施之外的调用方需要访问
- 多个调用方需要对同一个 Server 有不同级别的访问权限
- 你需要在事后回答"具体是哪个调用方做的"——为了审计、事故调查,或监管问询
- 被调用的工具会移动资金、拒绝某件事,或者产生对调用方之外的人有真实后果的决定

## 实例:同一个决策在三个 POC 里的三个时间点

[`claims-mcp-oauth-poc`](https://github.com/xingaiapp/xingai-enterprise-ai-pocs/tree/main/pocs/claims-mcp-oauth-poc) 从一开始就实现了真实的 OAuth 2.1 + PKCE + JWT([ADR-006](https://github.com/xingaiapp/xingai-enterprise-ai-pocs/blob/main/docs/adr/006-claims-mcp-oauth-poc-real-auth.zh.md))——它存在的全部意义就是证明这套认证协议本身能用在理赔裁决上,所以用静态 Key 会直接违背这个 POC 的目的。

[`claims-partner-api-mcp-poc`](https://github.com/xingaiapp/xingai-enterprise-ai-pocs/tree/main/pocs/claims-partner-api-mcp-poc) 反而用了一个单一的静态 bearer token([ADR-007](https://github.com/xingaiapp/xingai-enterprise-ai-pocs/blob/main/docs/adr/007-claims-partner-api-mcp-poc-full-coverage.zh.md))——不是因为认证不重要,而是因为那个 POC 的目的是证明完整的 18 个端点能干净地映射成 MCP 工具,如果同时给 18 个工具做真实认证,会很难分清一个 bug 到底是出在 API 映射上还是认证检查上。静态 Key 被明确列为头号"尚未生产就绪"事项,而不是被悄悄略过——而且 ADR-007 写清楚了具体的组合方案:把 `claims-mcp-oauth-poc` 的 Authorization Server 接到这个 Server 前面,强制执行 OpenAPI 契约里已经声明好的 10 个 scope。

[`claims-workflow-v2-poc`](https://github.com/xingaiapp/xingai-enterprise-ai-pocs/tree/main/pocs/claims-workflow-v2-poc) 是这条线上最新的一点([ADR-009](https://github.com/xingaiapp/xingai-enterprise-ai-pocs/blob/main/docs/adr/009-claims-workflow-v2-mcp-multiagent.zh.md))。它的 MCP Server 目前只有一个调用方——自己的 Supervisor 进程——所以按上面的框架,今天用一个静态内部服务 Token 确实够用。但它的四个工具分别标了 `policy.read`、`audit.write`、`audit.read`、`payments.write`——直接复用 `claims-mcp-oauth-poc` 和 `claims-partner-api-mcp-poc` 已有的 scope 词汇表,而不是自己发明新名字。这个赌注是:如果/当真的有第三方厂商需要直接调用这个 Server,把真实的 Authorization Server 接上去只是对着已经存在的名字做一次 scope 映射,而不是重新设计。这是这次迁移里便宜的那部分,今天零成本就做完了,专门是为了让真正需要花钱的那部分(签发和轮换真实的按合作方区分的凭证)成为将来唯一要做的事。

## 双墙模型:为什么光有 OAuth Scope 也不够

`claims-mcp-oauth-poc` 没有止步于 OAuth scope。一个带 `claims.adjudicate` 的 Token 还要经过第二道独立的检查——一个赔付授权策略:理赔类型白名单加金额上限,用 OAuth 层完全不知道的代码强制执行。这一点很关键,因为 scope 回答的是一个没有金额概念的是非题("这个 Token 到底能不能裁决理赔")。第二道墙才是阻止一个 scope 正确、但被攻破或被过度信任的 Token 去授权一笔灾难性赔付的东西。跳过这道墙、把 OAuth scope 当成已经足够,是企业 MCP 里一个常见的错误:一个宽泛的 scope 授权读起来就像"已完全授权",而 OAuth 本身不会告诉你这和"任意金额、任意理赔类型、没有上限"根本不是一回事。

## 这套方案解决不了什么

静态 Key 也好,OAuth 2.1 也好,单靠它们都解决不了:按合作方限流、租户数据隔离、Key/Token 泄露检测,或者一份泄露凭证的真实应急响应手册。这些是本文没有覆盖的独立设计问题——这里想说清楚的是一件更窄的事:针对你实际拥有的信任边界,选对认证原语,并在自己的设计文档里诚实地说明哪个是已经建好的、哪个只是计划中的。

## 相关

- [ADR-006:Claims MCP OAuth POC——真实认证,不是占位符](https://github.com/xingaiapp/xingai-enterprise-ai-pocs/blob/main/docs/adr/006-claims-mcp-oauth-poc-real-auth.zh.md)——双墙模型的来源
- [ADR-007:Claims Partner API MCP POC——完整 API 覆盖,认证推迟](https://github.com/xingaiapp/xingai-enterprise-ai-pocs/blob/main/docs/adr/007-claims-partner-api-mcp-poc-full-coverage.zh.md)——"先对齐 scope 命名、认证以后再接"这套模式的来源
- [ADR-009:理赔工作流 v2——MCP、LLM Agent、LangGraph Supervisor](https://github.com/xingaiapp/xingai-enterprise-ai-pocs/blob/main/docs/adr/009-claims-workflow-v2-mcp-multiagent.zh.md)——本文最新的实例
- [MCP API Coverage vs. Workflow Tools](2026-07-13-mcp-api-coverage-vs-workflow-tools.zh.md)——用同样两个 POC 讨论的另一个相关取舍(工具面,不是认证)
- [How MCP Works in Production: A Deep Dive from Robinhood Trading MCP](2026-07-11-mcp-in-production-robinhood-case.zh.md)——双墙模型的最初来源,从券商领域移植到这里
- [Agent Governance Reference Architecture](2026-07-05-agent-governance-reference-architecture.zh.md)——本文可审计性这一点所处的更大的 authority/provenance/approval/audit 框架
