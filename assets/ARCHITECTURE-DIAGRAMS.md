# Enterprise AI Architecture Diagrams

这个文件包含了文章中所有核心概念的高分辨率架构图表。

## Evidence Engine + Eval Registry (UX)

PNG diagram — worker/cache verification pipeline with EEE eval gate (not a product UI):

![Evidence Engine + Eval Registry UX](./evidence-engine-eval-registry-system-design-ux.png)

Used in:

- [Evidence Engine + Eval Registry (EN)](../articles/2026-07-26-evidence-engine-eval-registry.md)
- [Evidence Engine + Eval Registry (中文)](../articles/2026-07-26-evidence-engine-eval-registry.zh.md)
- [xingai-evidence-engine](https://github.com/xingaiapp/xingai-evidence-engine)
- [xingai-eval-registry](https://github.com/xingaiapp/xingai-eval-registry)

---

## Orchestrator vs MCP Gateway (UX)

PNG diagram for dev teams — **no separate Orchestration MCP**:

![Orchestrator vs MCP Gateway UX](./orchestrator-vs-mcp-gateway-ux.png)

Used in:

- [Orchestrator vs MCP Gateway (EN)](../articles/2026-06-13-orchestrator-vs-mcp-gateway.md)
- [Orchestrator 与 MCP Gateway (中文)](../articles/2026-06-13-orchestrator-vs-mcp-gateway.zh.md)
- [XingAI Enterprise Agent Platform (POC repo)](https://github.com/xingaiapp/xingai-enterprise-ai-pocs/blob/main/docs/ENTERPRISE-AGENT-PLATFORM.md)

---

## Claims Settlement Workflow v2 (XingAI corrected design)

SVG diagram — nine-stage claims pipeline with the three structural fixes: a split **Fraud Triage / Fraud Scoring** pair around damage assessment, an explicit **Case Resolution Router** with labeled return paths (replacing a single generic escalation box), and a cross-cutting **Compliance & Audit Trail Agent** lane. XingAI-branded footer credits the author and links back to xingai.app.

![Claims Settlement Workflow v2 — XingAI corrected design](./claims-workflow-v2-xingai-branded.svg)

Used in:

- [Redesigning the Agentic Claims Workflow (EN)](../articles/2026-07-14-claims-workflow-redesign-fraud-routing-audit.md)
- [重新设计理赔工作流 (中文)](../articles/2026-07-14-claims-workflow-redesign-fraud-routing-audit.zh.md)
- [claims-workflow-v2-poc (runnable POC repo)](https://github.com/xingaiapp/xingai-enterprise-ai-pocs/tree/main/pocs/claims-workflow-v2-poc) — implements this exact design end to end

---

## 1. 企业 AI 决策系统完整架构

```mermaid
flowchart TD
    A["用户/企业事件"] -->|1. 认证| B["🔐 安全层<br/>OAuth, RBAC, 密钥"]
    
    B -->|2. 发布事件| C["📨 事件总线<br/>Kafka / Service Bus"]
    
    C -->|3. 路由| D["🤖 智能体编排器<br/>生命周期、路由、错误"]
    
    D -->|4. 上下文化| E["💾 记忆层<br/>短期、长期、组织级"]
    
    D -->|5. 访问工具| F["🔧 MCP 工具网关<br/>GitHub, Slack, 数据库"]
    
    F -->|6. 执行工具| G["🌐 外部系统<br/>APIs, 数据库, 服务"]
    
    D -->|7. 准备决策| H["👤 人工批准层<br/>审核、批准、拒绝、上报"]
    
    H -->|8. 日志和监控| I["📊 可观测性层<br/>指标、日志、追踪"]
    
    H -->|9. 审计追踪| J["⚖️ 治理与合规<br/>审计、隐私、公平性、法律"]
    
    J -->|最终决策| K["✅ 响应给用户"]
    
    style B fill:#ff6666,stroke:#cc0000,color:#fff
    style C fill:#ff9966,stroke:#cc6600,color:#000
    style D fill:#ffcc66,stroke:#cc9900,color:#000
    style E fill:#99ff99,stroke:#00cc00,color:#000
    style F fill:#66ff99,stroke:#00cc00,color:#000
    style H fill:#66ccff,stroke:#0099ff,color:#000
    style I fill:#9966ff,stroke:#6600cc,color:#fff
    style J fill:#ff66ff,stroke:#cc00cc,color:#fff
    style K fill:#00ff00,stroke:#00cc00,color:#000
```

## 2. AI 系统成熟度演进

```mermaid
flowchart LR
    A["Level 1<br/>AI 聊天机器人<br/>LLM only"] -->|功能↑| B["Level 2<br/>RAG 系统<br/>检索增强"]
    
    B -->|自动化↑| C["Level 3<br/>AI 智能体<br/>LLM + RAG + MCP"]
    
    C -->|协作↑| D["Level 4<br/>多智能体系统<br/>编排 + 事件总线"]
    
    D -->|可信度↑| E["Level 5<br/>AI 决策系统<br/>完整企业架构"]
    
    A -->|企业就绪| A1["❌ 不就绪"]
    B -->|企业就绪| B1["⚠️ 部分"]
    C -->|企业就绪| C1["⚠️ 部分"]
    D -->|企业就绪| D1["⚠️ 部分"]
    E -->|企业就绪| E1["✅ 完全就绪"]
    
    style A fill:#ff9999
    style B fill:#ffcc99
    style C fill:#ffff99
    style D fill:#99ff99
    style E fill:#99ccff
```

## 3. 演示栈 vs 企业栈

```mermaid
flowchart LR
    subgraph Demo["🎭 演示栈<br/>快速但不可靠"]
        A["Frontend"] --> B["Agent"]
        B --> C["RAG"]
        C --> D["LLM"]
        D --> E["MCP"]
        E --> F["DB"]
    end
    
    subgraph Enterprise["🏢 企业栈<br/>成熟且可信"]
        G["用户"] --> G1["Auth"]
        G1 --> G2["Event Bus"]
        G2 --> G3["Orchestrator"]
        G3 --> G4["Memory"]
        G3 --> G5["LLM"]
        G3 --> G6["MCP Gateway"]
        G6 --> G7["Tools"]
        G3 --> G8["Approval"]
        G8 --> G9["Observability"]
        G9 --> G10["Governance"]
        G10 --> G11["Decision"]
    end
    
    style Demo fill:#ffcccc
    style Enterprise fill:#ccffcc
```

## 4. 事件总线的作用

```mermaid
flowchart TD
    subgraph Without["❌ 没有事件总线<br/>紧密耦合、难以扩展"]
        A["系统 A"] -->|直接调用| B["AI Agent"]
        B -->|直接修改| C["系统 B"]
        
        D["问题"] --> D1["系统间依赖"]
        D --> D2["无法并行"]
        D --> D3["难以审计"]
        D --> D4["无法扩展"]
    end
    
    subgraph With["✅ 有事件总线<br/>解耦、可扩展"]
        E["系统 A"] -->|发布| F["事件总线"]
        F -->|订阅| G["AI 分析"]
        F -->|订阅| H["合规检查"]
        F -->|订阅| I["风险评估"]
        F -->|订阅| J["审计日志"]
        
        K["优势"] --> K1["系统解耦"]
        K --> K2["并行处理"]
        K --> K3["完整审计"]
        K --> K4["无限扩展"]
    end
    
    style Without fill:#ffcccc
    style With fill:#ccffcc
```

## 5. 记忆层架构

```mermaid
flowchart TD
    A["用户交互"] --> B["三层记忆"]
    
    B --> B1["⏱️ 短期记忆<br/>作用域：单个请求<br/>生命周期：分钟<br/>例：当前用户输入"]
    
    B --> B2["📅 长期记忆<br/>作用域：用户生命周期<br/>生命周期：月/年<br/>例：用户偏好、历史"]
    
    B --> B3["🏢 组织级记忆<br/>作用域：系统范围<br/>生命周期：年<br/>例：政策、规则"]
    
    B1 --> C["更好的决策"]
    B2 --> C
    B3 --> C
    
    C --> D["个性化响应<br/>符合规制<br/>持续学习"]
    
    style B1 fill:#99ffff
    style B2 fill:#99ccff
    style B3 fill:#9999ff
    style C fill:#ffff99
```

## 6. 人工批准层流程

```mermaid
flowchart TD
    A["AI 决策<br/>推荐行动"] --> B["为人工审核准备"]
    
    B --> B1["📊 决策摘要"]
    B --> B2["⚠️ 风险评估"]
    B --> B3["📈 相关背景"]
    B --> B4["💡 可解释性"]
    
    B1 --> C["👤 人工审核"]
    B2 --> C
    B3 --> C
    B4 --> C
    
    C --> D1["✅ 批准"]
    C --> D2["❌ 拒绝"]
    C --> D3["🔄 修改"]
    C --> D4["⬆️ 上报"]
    
    D1 --> E["🎯 执行决策"]
    D2 --> E
    D3 --> E
    D4 --> E
    
    E --> F["📝 记录结果"]
    
    style A fill:#ff9999
    style C fill:#ffff99
    style E fill:#99ff99
    style F fill:#9999ff
```

## 7. MCP 在企业 AI 中的角色

```mermaid
flowchart TD
    A["🤖 智能体"] -->|决策| B["🛣️ 工具路由器<br/>业务逻辑所在"]
    
    B -->|标准化| C["🔌 MCP 协议"]
    
    C -->|调用| D["🔧 工具"]
    
    D --> D1["GitHub"]
    D --> D2["Slack"]
    D --> D3["Notion"]
    D --> D4["数据库"]
    D --> D5["内部 API"]
    
    style A fill:#ff9999
    style B fill:#ffff99
    style C fill:#99ffcc
    style D fill:#99ccff
```

## 8. 可观测性三支柱

```mermaid
flowchart TD
    A["🔍 可观测性"] --> B["📈 指标"]
    A --> C["📝 日志"]
    A --> D["🔗 追踪"]
    
    B --> B1["决策数/分钟"]
    B --> B2["成功率"]
    B --> B3["延迟 p50/p99"]
    B --> B4["成本/决策"]
    
    C --> C1["决策输入"]
    C --> C2["推理步骤"]
    C --> C3["工具调用"]
    C --> C4["执行结果"]
    
    D --> D1["请求入口"]
    D --> D2["智能体路由"]
    D --> D3["工具调用序列"]
    D --> D4["最终决策"]
    
    style A fill:#ff9966
    style B fill:#ffcc99
    style C fill:#ffcc99
    style D fill:#ffcc99
```

## 9. 案例：投资决策的完整流程

```mermaid
flowchart TD
    A["用户请求<br/>应该买 TSLA 吗？"] --> B["🔐 安全层验证"]
    
    B --> C["📨 发布到事件总线"]
    
    C --> D["🤖 分析智能体"]
    C --> E["✅ 合规检查"]
    C --> F["⚠️ 风险评估"]
    
    D --> G["💡 生成推荐<br/>信心: 78%"]
    E --> G
    F --> G
    
    G --> H["👤 投资者审核"]
    
    H -->|批准| I["💳 执行交易"]
    H -->|拒绝| J["🚫 取消"]
    
    I --> K["📝 记录到审计追踪"]
    J --> K
    
    K --> L["⚖️ SEC 合规证明"]
    
    style A fill:#ff9999
    style B fill:#ff6666,color:#fff
    style C fill:#ff9966
    style D fill:#99ff99
    style G fill:#ffff99
    style H fill:#ccffff
    style I fill:#99ff99
    style K fill:#9966ff,color:#fff
    style L fill:#ff66ff,color:#fff
```

## 10. XingAI 产品架构示意

```mermaid
flowchart TD
    A["🍽️ Meal Coach<br/>健康决策"] --> A1["记忆层<br/>饮食限制、偏好"]
    A1 --> A2["AI 推荐<br/>个性化餐饮"]
    
    B["💰 Invest AI<br/>投资决策"] --> B1["记忆层<br/>风险档案、目标"]
    B1 --> B2["AI 推荐<br/>个性化投资"]
    
    C["✈️ Travel AI<br/>旅行决策"] --> C1["记忆层<br/>预算、偏好"]
    C1 --> C2["AI 推荐<br/>个性化行程"]
    
    A2 --> D["🎯 更好的决策"]
    B2 --> D
    C2 --> D
    
    D --> E["信任 + 参与 + 结果"]
    
    style A fill:#ff9999
    style B fill:#99ff99
    style C fill:#99ccff
    style D fill:#ffff99
    style E fill:#ff66ff,color:#fff
```

---

## 使用说明

这些图表可以：
1. 在文章中嵌入（Mermaid 原生支持）
2. 导出为 PNG/SVG 在演示中使用
3. 在 GitHub Wiki 中引用
4. 用于团队培训和讲座

## 图表质量标准

- ✅ 清晰的颜色编码
- ✅ 标准化的图标和符号
- ✅ 一致的流程方向
- ✅ 可读的文本标签
- ✅ 适合演示和印刷
