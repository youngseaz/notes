

## 概述

QUIC (Quick UDP Internet Connections) 是一个安全的通用传输协议，最初由Google开发，后由IETF标准化。
- QUIC基于UDP实现，提供了类似TCP的可靠性保障
- 不支持明文传输，只支持TLS 1.3安全传输。


![QUIC/HTTP3 分层模型及与 HTTP2 对比图](<images/01 quic协议介绍/image.png>)
<div align="center">HTTP2 vs QUIC/HTTP3</div>


| 对比维度       | HTTP/1.1         | HTTP/2          | HTTP/3（QUIC）    |
| --------- | ---------------- | --------------- | --------------- |
| 发布时间      | 1997年            | 2015年           | 2022年（RFC 9114） |
| 底层协议      | TCP              | TCP             | UDP + QUIC      |
| 连接建立      | TCP握手 + TLS握手    | TCP握手 + TLS握手   | QUIC集成TLS 1.3   |
| 首次连接延迟    | 2~3 RTT（HTTPS）   | 2~3 RTT（HTTPS）  | 1 RTT           |
| 重连优化      | 无                | 无               | 支持 0-RTT        |
| 请求处理方式    | 串行（Pipeline很少使用） | 多路复用            | 多路复用            |
| Header压缩  | 无                | HPACK           | QPACK           |
| HTTP层队头阻塞 | 有                | 无               | 无               |
| TCP层队头阻塞  | 有                | 有               | 无               |
| 丢包影响      | 影响整个连接           | 影响整个连接          | 仅影响对应Stream     |
| 连接迁移      | 不支持              | 不支持             | 支持              |
| 移动网络切换    | 需要重连             | 需要重连            | 通常无需重连          |
| 加密要求      | 可选               | 可选（实际基本强制HTTPS） | 强制TLS 1.3       |
| 协议升级难度    | 内核TCP限制          | 内核TCP限制         | 用户态实现，升级方便      |
| 抓包分析      | 容易               | 较容易             | 困难              |
| 实现复杂度     | 低                | 中               | 高               |
| CPU开销     | 低                | 中               | 较高              |



# QUIC协议参考文档总结

## 核心RFC文档
 

- [RFC 9000: QUIC: A UDP-Based Multiplexed and Secure Transport](https://www.rfc-editor.org/info/rfc9000/)

- [RFC 9001: Using TLS to Secure QUIC](https://www.rfc-editor.org/info/rfc9001/) 

- [RFC 9002: QUIC Loss Detection and Congestion Control](https://www.rfc-editor.org/info/rfc9002/)
- [RFC 9114: HTTP/3](https://www.rfc-editor.org/info/rfc9114/)
- [RFC 9204: QPACK](https://www.rfc-editor.org/info/rfc9204/)


## QUIC协议栈

```
+---------------+
|    HTTP/3    |  RFC 9114
+---------------+
|    QPACK     |  RFC 9204
+---------------+
|     QUIC     |  RFC 9000
+---------------+
|  TLS 1.3     |  RFC 9001
+---------------+
|  UDP          |
+---------------+
|    IP         |
+---------------+
```

## 安全考虑

1. **握手DoS防护**: 地址验证，放大攻击缓解
2. **0-RTT重放**: 警告潜在重放攻击风险
3. **连接迁移安全**: peer地址欺骗防护
4. **Header Protection**: 防止流量分析

## 性能优势

1. **低延迟**: 0-RTT数据发送
2. **无队头阻塞**: 多路复用streams独立
3. **更好的拥塞控制**: 连接级而非stream级
4. **连接迁移**: 网络变化时保持连接

## 实现参考

| 实现 | 语言 | 备注 |
|-----|------|-----|
| lsquic | C | - |
| quiche | Rust | - |
| ngtcp2 | C | - |
| aioquic | Python | - |



## 相关链接

- IETF QUIC Working Group: https://datatracker.ietf.org/wg/quic/about/
- RFC 9000: https://www.rfc-editor.org/rfc/rfc9000
- RFC 9001: https://www.rfc-editor.org/rfc/rfc9001
- RFC 9002: https://www.rfc-editor.org/rfc/rfc9002
- RFC 9114: https://www.rfc-editor.org/rfc/rfc9114
- RFC 9204: https://www.rfc-editor.org/rfc/rfc9204