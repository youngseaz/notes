



```c
lsquic_engine_packet_in()            ← 唯一的网络入口
  ├─ parse_packet_in_begin()         ← 解析报文头（分IETF/gQUIC/Q046/Q050版本）
  ├─ process_packet_in()             ← 连接路由
  │   ├─ find_or_create_conn()       ← 按CID查找或创建连接
  │   │   ├─ mini_conn (握手阶段)
  │   │   └─ full_conn (完整连接)
  │   └─ conn->ci_packet_in()        ← 注入报文到连接
  │       ├─ decrypt_packet()        ← 解密
  │       └─ process_regular_packet()← 解析并处理帧
  └─ lsquic_engine_process_conns()   ← 驱动连接处理



```



## lsquic 框架架构分析

### 一、整体架构分层

```
┌─────────────────────────────────────────────────────────┐
│                    用户应用层                            │
│  (on_new_conn, on_stream_read, packets_out 回调)        │
├─────────────────────────────────────────────────────────┤
│                      lsquic_engine                      │
│             连接调度 / 报文分发 / tick队列                │
├──────────────────┬──────────────────┬───────────────────┤
│    mini_conn     │   full_conn      │   full_conn_ietf  │
│  (握手期轻量连接) │ (gQUIC完整连接)   │ (IETF QUIC完整连接)│
├──────────────────┴──────────────────┴───────────────────┤
│                    stream 层                            │
│            流管理 / 流控 / 优先级排序                     │
├──────────────────┬──────────────────┬───────────────────┤
│    帧解析层       │   QPACK/HPACK     │   加密会话层      │
│  parse_funcs 虚表  │  (HPACK编码器)    │  (TLS/QUIC加密) │
├──────────────────┴──────────────────┴───────────────────┤
│                    网络I/O层                             │
│            packet_in / packet_out 生命周期               │
└─────────────────────────────────────────────────────────┘
```

### 二、核心类型体系

| 类型 | 定义位置 | 说明 |
|---|---|---|
| `lsquic_engine_t` | lsquic_engine.c | 引擎主对象，管理所有连接 |
| `lsquic_conn_t` | lsquic_conn.h | 连接抽象基类（`conn_iface` 虚表） |
| `lsquic_stream_t` | `lsquic_stream.c` | QUIC Stream 实现 |
| `lsquic_packet_in_t` | lsquic_packet_in.h | 输入报文（来自网络） |
| `lsquic_packet_out_t` | `lsquic_packet_out.h` | 输出报文（要发送的） |
| `lsquic_time_t` | lsquic_int_types.h | `uint64_t`，微秒级时间 |
| `lsquic_packno_t` | lsquic_int_types.h | `uint64_t`，包序号 |
| `lsquic_cid_t` | lsquic_types.h | 连接ID（最大20字节） |

### 三、引擎核心 lsquic_engine.c

**生命周期：**
```
lsquic_engine_new()        创建引擎（server/client）
  └─ lsquic_engine_packet_in()   注入网络报文
      └─ parse_packet_in_begin()  解析报文头
      └─ process_packet_in()      路由到连接
          ├─ find_or_create_conn() 按CID查找/创建
          │   ├─ 新连接 → mini_conn_new()
          │   └─ 已有 → ci_packet_in() 注入
          └─ ci_tick()             驱动连接处理

lsquic_engine_process_conns()  处理所有可tick连接
  └─ ci_tick() → ci_next_packet_to_send() → ci_packet_sent()

lsquic_engine_destroy()        销毁引擎
```

**flags:**
- `LSENG_SERVER` — 服务端模式
- `LSENG_HTTP` — HTTP模式
- `LSENG_HTTP_SERVER = LSENG_SERVER | LSENG_HTTP`

### 四、连接架构：虚表多态

```
struct conn_iface {                    ← 虚表 (lsquic_conn.h)
    ci_tick()                         ← 定时处理
    ci_packet_in()                    ← 接收报文
    ci_next_packet_to_send()          ← 取待发送包
    ci_packet_sent() / _not_sent()    ← 发送确认
    ci_destroy()                      ← 销毁
    ci_is_tickable()                  ← 是否可调度
    ci_hsk_done()                     ← 握手完成回调
    ...
};

mini_conn_iface_standard  (mini_conn.c)  ── gQUIC握手连接
mini_conn_iface_standard_Q050  (mini_conn.c)  ── Q050握手连接

full_conn / ietf_full_conn → 各自实现 conn_iface
```

**mini_conn → full_conn 的晋升：**
```
mini_conn_ci_tick() 返回 TICK_PROMOTE
  → lsquic_engine 调用 gquic_full_conn_server_new()
  → mini_conn 的 state 转移给 full_conn
  → full_conn 接管后续处理
```

### 五、帧解析层：`parse_funcs` 虚表

```
struct parse_funcs {                   ← 版本特定的帧解析/生成 (lsquic_parse.h)
    pf_gen_reg_pkt_header()          生成报文头
    pf_parse_frame_type()            解析帧类型
    pf_parse_stream_frame()          解析STREAM帧
    pf_parse_ack_frame()             解析ACK帧
    pf_parse_handshake_done_frame()  解析HANDSHAKE_DONE
    pf_gen_ack_frame()               生成ACK帧
    ...
};

各版本实现：
  lsquic_parse_gquic_be.c    →  gQUIC大端 (Q043-Q046)
  lsquic_parse_Q046.c        →  Q046
  lsquic_parse_Q050.c        →  Q050
  lsquic_parse_ietf_v1.c     →  IETF v1/v2
```

**帧分发流程：**
```
process_regular_packet()
  → pf_parse_frame_type(buf[0])     ← 从首字节查表确定帧类型
  → process_frames[type](conn, p)   ← 根据类型分发到具体处理器
      ├─ process_ack_frame()        → pf_parse_ack_frame()
      ├─ process_stream_frame()     → pf_parse_stream_frame()
      ├─ process_handshake_done_frame() → pf_parse_handshake_done_frame()
      └─ ...
```

### 六、Stream 层

```
lsquic_stream.c
  └─ 流状态机: IDLE → OPEN → HALF_CLOSED → CLOSED
  └─ 重要API:
      lsquic_stream_read()         读取流数据
      lsquic_stream_write()        写入流数据
      lsquic_stream_shutdown()     关闭流
      lsquic_stream_wantread()     注册读事件
      lsquic_stream_wantwrite()    注册写事件
```

**流控：**
- 连接级流控 (`lsquic_cfcw.c`)
- Stream级流控 (`lsquic_sfcw.c`)
- 接收历史 (`lsquic_rechist.c`)

### 七、加密层

```
lsquic_enc_sess.h  → 加密会话抽象接口
  esf_create_server()      创建服务端加密会话
  esf_create_client()      创建客户端加密会话
  esf_handle_chlo()        处理CHLO消息
  esf_decrypt_packet()     解密报文
  esf_encrypt_packet()     加密报文

实现:
  lsquic_enc_sess_ietf.c  → IETF QUIC (TLS 1.3)
  内置 gQUIC 实现          → Google QUIC (自定义加密)
```

### 八、QPACK/HPACK

```
ls-qpack/lsqpack.c       → QPACK 编解码器
  lsqpack_enc_encode()   编码头块
  lsqpack_dec_enc_in()   解码编码器流
  lsqpack_dec_header_in() 解码头块

lsquic_qenc_hdl.c        → QPACK编码器处理器
lsquic_qdec_hdl.c        → QPACK解码器处理器
```



