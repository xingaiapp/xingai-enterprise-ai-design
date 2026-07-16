# 实验：Model Adapter 契约

English: [lab.md](lab.md)

实现确定性 Fake Adapter，支持类型化 Final/Tool Action、超时模拟、畸形输出拒绝和十个评估案例。添加一份 ADR，对比直接调用厂商与 Adapter。达到 80% 通过；任何静默接受无效输出的行为自动判定失败。

