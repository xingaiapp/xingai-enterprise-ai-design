# Operations Runbooks

Chinese: [runbooks.zh.md](runbooks.zh.md)

For every incident: declare severity and commander, stop unsafe writes, preserve evidence, identify affected tenants, communicate, mitigate, validate recovery, and schedule a blameless corrective review.

| Trigger | Immediate containment | Recovery evidence |
|---|---|---|
| Unsafe action | Disable write tools; preserve trace/audit | Authorization and approval tests pass |
| Cross-tenant result | Stop retrieval; revoke affected index/version | Zero-leak regression suite passes |
| Model degradation | Route to approved fallback or manual review | Eval gate and canary pass |
| Authorization outage | Fail closed for protected actions | Policy service and negative tests healthy |
| Audit write failure | Block consequential writes | Durable audit continuity verified |
| Queue/backlog | Apply backpressure; pause proactive loops | Queue age and SLO recover |
| Cost spike | Lower budgets; disable nonessential agents | Unit-cost trend returns within budget |

