# 双语文章发布规范

## 概述

本仓库中的所有文章均以双语形式发布：英文（`.md`）+ 中文（`.zh.md`）。

## 文件命名规范

```
YYYY-MM-DD-slug.md        # 英文版本
YYYY-MM-DD-slug.zh.md     # 中文版本
```

示例：
```
2026-06-07-enterprise-ai-decision-systems.md      # English
2026-06-07-enterprise-ai-decision-systems.zh.md   # 中文
```

## 英文版本要求

### 文章结构

```markdown
---
title: Article Title
author: Author Name
date: 2026-06-07
tags: [tag1, tag2, tag3]
description: Brief description for SEO
---

# Article Title

[Opening paragraph]

## Section 1

[Content]

## Section 2

[Content]

---

**Author:** Name  
**Published:** June 7, 2026  
**Tags:** architecture, enterprise, ai
```

### 写作风格

- **目标受众** — Enterprise Architects, AI Architects, CTOs
- **语气** — 专业、观点鲜明、实践导向
- **长度** — 2500-3500 字
- **参考** — Medium Top Writer 级别、Microsoft Architecture Center、AWS Architecture Blog

### SEO 要求

- 清晰的文章标题（50-60 字符）
- 元描述（150-160 字符）
- 合理的标题层级（H1、H2、H3）
- 内部链接
- 相关标签（5-8 个）

## 中文版本要求

### 翻译原则

1. **不是逐字翻译** — 理解原意后用自然的中文表达
2. **保留专业术语** — 如 "Event Bus"、"MCP"、"Agent Orchestration"
3. **文化适应** — 使用中国企业架构师能理解的例子
4. **一致性** — 同一术语在全文中使用相同的翻译

### 常用术语对照表

| English | 中文 | 说明 |
|---------|------|------|
| AI Decision System | AI 决策系统 | 核心概念 |
| Enterprise Architecture | 企业架构 | |
| Event Bus | 事件总线 | 系统集成 |
| MCP | MCP 协议 | Model Context Protocol 的缩写，保持英文 |
| Agent Orchestration | 智能体编排 | 或"代理编排" |
| Human-in-the-Loop | 人机闭环 | 或"人工介入" |
| Memory Layer | 记忆层 | 系统架构组件 |
| Observability | 可观测性 | 系统监控 |
| RAG | RAG | Retrieval-Augmented Generation，保持缩写 |
| LLM | 大语言模型 / LLM | 根据上下文选择 |
| Tool Gateway | 工具网关 | MCP 工具集成点 |
| Governance & Compliance | 治理与合规 | |

## 发布流程

1. **英文版本优先** — 先完成英文草稿
2. **审核英文** — 内部审阅和反馈
3. **翻译中文** — 翻译英文版本
4. **并行发布** — 同时发布两个版本
5. **更新 README** — 在文章表格中添加链接

## 文件放置

所有文章存放在 `articles/` 目录：

```
articles/
├── 2026-06-07-enterprise-ai-decision-systems.md
├── 2026-06-07-enterprise-ai-decision-systems.zh.md
├── 2026-06-08-event-bus-patterns.md
└── 2026-06-08-event-bus-patterns.zh.md
```

## Markdown 最佳实践

### 代码块

```markdown
# 英文
\`\`\`python
# Code example
\`\`\`

# 中文
\`\`\`python
# 代码示例
\`\`\`
```

### 链接

```markdown
[Link Text](url)  # 英文

[链接文本](url)   # 中文
```

### 图片

```markdown
![Alt text](../assets/image-name.png)
```

### Mermaid 图表

可以在两个版本中都使用相同的 Mermaid 代码，或为中文版本添加中文标签。

## 检查清单

发布前：

- [ ] 英文版本已完成
- [ ] 英文语法和拼写正确
- [ ] 中文版本已完成
- [ ] 中文表达自然流畅
- [ ] 术语翻译一致
- [ ] 两个版本包含相同的代码和图表
- [ ] SEO 元数据已添加
- [ ] 链接有效
- [ ] 标签准确
- [ ] README 已更新

## 问题？

如有问题，参考：
- [Tech Blog 的双语规范](https://github.com/xingaiapp/xingai-tech-blog/blob/main/docs/BILINGUAL-POSTS.md)
- 现有的已发布文章
