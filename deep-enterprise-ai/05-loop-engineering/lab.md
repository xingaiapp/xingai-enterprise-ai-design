# Lab: Durable Loop Contract

Chinese: [lab.zh.md](lab.zh.md)

Extend `LoopState` with checkpoint serialization, a no-progress counter, maximum revisions, cancellation, and one compensation transition. Test restart, duplicate event, illegal transition, budget exhaustion, and successful replay. Pass at 80%; duplicate side effects fail the lab.

