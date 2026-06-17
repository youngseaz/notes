# QUIC协议参考文档总结

## 概述

QUIC (Quick UDP Internet Connections) 是一个安全的通用传输协议，最初由Google开发，后由IETF标准化。QUIC基于UDP实现，提供了类似TCP的可靠性保障，同时集成了TLS 1.3安全握手。

## 核心RFC文档

### 1. RFC 9000 - QUIC Transport Protocol (2021年5月)

**标题**: QUIC: A UDP-Based Multiplexed and Secure Transport

**主要内容**:

#### 1.1 核心特性
- **连接oriented**: 客户端-服务器模型
- **流 multiplexing**: 支持多路复用 streams
- **低延迟连接建立**: 0-RTT 和 1-RTT 握手
- **连接迁移**: 支持网络路径切换
- **安全**: 集成TLS，端到端加密

#### 1.2 Stream (流)
- **类型**: 单向(uni-directional)和双向(bi-directional)
- **ID结构** (最低2位):
  - `0x00`: 客户端发起，双向
  - `0x01`: 服务器发起，双向
  - `0x02`: 客户端发起，单向
  - `0x03`: 服务器发起，单向
- **状态机**: Ready → Send → Data Sent → Data Recvd
- **流量控制**: 基于信用(credit)的方案

#### 1.3 连接 (Connection)
- **Connection ID**: 用于标识连接的不可透明ID
- **版本协商**: 支持版本协商包
- **地址验证**: 防止放大攻击
- **连接迁移**: 使用连接ID实现

#### 1.4 握手流程
```
Client                                          Server
  |                                               |
  |--- Initial (ClientHello) -------------------->|  1-RTT开始
  |<-- Initial (ServerHello, EncryptedExtensions)-|
  |<-- Handshake (Finished) ----------------------|
  |--- Handshake (Finished) --------------------->|
  |                                               |
  |<======== 1-RTT 数据开始 ===========>|
```

#### 1.5 包格式

**长头包** (Long Header):
- Initial: 首次握手，0-RTT数据之前
- 0-RTT: 早期数据(需要之前会话)
- Handshake: 握手中的后续包
- Retry: 地址验证

**短头包** (Short Header):
- 1-RTT: 连接建立后使用，更简洁的头部

#### 1.6 帧类型 (Frames)
- PADDING, PING, ACK, CRYPTO
- STREAM, MAX_DATA, MAX_STREAM_DATA
- NEW_CONNECTION_ID, PATH_CHALLENGE
- CONNECTION_CLOSE, HANDSHAKE_DONE

#### 1.7 丢包检测
- **Packet Threshold**: 3个包
- **Time Threshold**: 9/8 × max(smoothed_rtt, latest_rtt)

#### 1.8 连接终止
- Idle Timeout
- Immediate Close
- Stateless Reset

---

### 2. RFC 9001 - Using TLS to Secure QUIC (2021年5月)

**标题**: Using TLS to Secure QUIC

**主要内容**:

#### 2.1 TLS集成
- 使用TLS 1.3作为密钥协商
- CRYPTO帧承载TLS握手消息
- 四层加密级别: Initial → 0-RTT → Handshake → 1-RTT

#### 2.2 0-RTT
- 允许客户端在握手完成前发送数据
- 基于session ticket恢复会话
- **安全注意**: 存在重放攻击风险

#### 2.3 密钥更新
- QUIC有自己的密钥更新机制
- 使用KEY_UPDATE错误码

#### 2.4 包保护
- AEAD (AES-128-GCM, AES-256-GCM, ChaCha20-Poly1305)
- Header Protection: 混淆包头

---

### 3. RFC 9002 - QUIC Loss Detection and Congestion Control (2021年5月)

**标题**: QUIC Loss Detection and Congestion Control

**主要内容**:

#### 3.1 RTT估计
```python
smoothed_rtt = 7/8 * smoothed_rtt + 1/8 * adjusted_rtt
rttvar = 3/4 * rttvar + 1/4 * |smoothed_rtt - adjusted_rtt|
```

#### 3.2 丢包检测
- **Packet Threshold**: 超过3个包判定丢失
- **Time Threshold**: 超时判定丢失
- **PTO (Probe Timeout)**: 探测超时
  ```
  PTO = smoothed_rtt + max(4*rttvar, kGranularity) + max_ack_delay
  ```

#### 3.3 拥塞控制
- **算法**: 类似TCP NewReno
- **最小窗口**: 2个包 (TCP是1个)
- **状态**: Slow Start → Recovery → Congestion Avoidance

#### 3.4 与TCP的关键差异
1. 独立的Packet Number Spaces
2. 单调递增的包号
3. 更清晰的丢失周期
4. 无Reneging (不允许撤销ACK)
5. 支持更多ACK范围
6. PTO替代RTO和TLP

---

### 4. RFC 9114 - HTTP/3 (2022年6月)

**标题**: HTTP/3

**主要内容**:

#### 4.1 概述
- HTTP语义在QUIC上的映射
- ALPN标识符: `h3`
- 默认端口: 443

#### 4.2 连接管理
- 发现: Alt-Svc头或HTTP/2 ALTSVC帧
- 连接重用: 验证证书匹配origin

#### 4.3 Stream映射
- 请求流: 客户端发起的双向流
- 推送流: 服务器发起的单向流
- 控制流: 传输SETTINGS等控制消息

#### 4.4 帧类型
- DATA, HEADERS, SETTINGS
- CANCEL_PUSH, PUSH_PROMISE
- GOAWAY, MAX_PUSH_ID

#### 4.5 错误码
- H3_NO_ERROR, H3_GENERAL_PROTOCOL_ERROR
- H3_REQUEST_INCOMPLETE, H3_REQUEST_CANCELLED

---

### 5. RFC 9204 - QPACK (2022年6月)

**标题**: QPACK: Field Compression for HTTP/3

**主要内容**:

#### 5.1 背景
- HPACK针对HTTP/2，不适合HTTP/3的乱序特性
- QPACK设计减少队头阻塞(head-of-line blocking)

#### 5.2 核心概念
- **Static Table**: 预定义的头部索引表
- **Dynamic Table**: 连接期间动态构建
- **Encoder/Decoder Stream**: 单向流传输指令

#### 5.3 阻塞控制
- Required Insert Count: 解码所需的基础表大小
- 动态表容量限制

#### 5.4 索引方式
- **Absolute Index**: entry生命周期内固定
- **Relative Index**: 相对于Base
- **Post-Base Index**: 用于相对较新的entry

---

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