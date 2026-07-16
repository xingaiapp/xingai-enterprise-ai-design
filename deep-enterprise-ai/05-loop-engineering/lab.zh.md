# 实验：Durable Loop 契约

English: [lab.md](lab.md)

为 `LoopState` 添加 Checkpoint 序列化、无进度计数、最大 Revision、取消与一个补偿转换。测试重启、重复事件、非法转换、预算耗尽与成功 Replay。达到 80% 通过；重复副作用判定失败。

