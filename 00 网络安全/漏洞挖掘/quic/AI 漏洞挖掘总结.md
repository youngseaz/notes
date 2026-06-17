
# AI漏洞挖掘

lsquic: 
- 363.3 k/loc
- C语言

## 整体思路
Harness Engineering（驭缰工程）： OpenAI 在 2026 年 2 月提出的工程范式：工程师不再写代码，而是设计环境、明确意图、构建反馈回路，让 AI 智能体可靠地完成工作。

>人类掌舵，智能体执行。

- 传统工程：人类写代码 → 机器执行代码
- Harness Engineering：人类设计约束 → 智能体写代码 → 机器执行代码

掌舵：
- 框架 -> 高危入口 -> 高危函数（优先级）
- fuzz -> Harness -> 种子生成
- 静态分析 -> 重点漏洞类型
- 不确定随机性 -> 人工约束


## 遇到的问题
- 上下文问题：agent（tools），LLM不一样,准确率和速度也不一样，glm5.1常常导致agent出现死循环问题，使用体验 GPT5.5 > deepseek v4 pro/flash > glm5.1
- 指令偏移：不按指令生成POC，生成POC修改代码
- AI幻觉：假想场景、局部代码片段问题误报

最优解：
- 结合 CI/CD 工程可以大大降低误报
- 端到端POC可能修改代码或者构建失败、函数POC需人判断合适的函数




# 整数溢出/越界读取


## 代码的作用

这段代码是 QUIC 传输参数解码循环中的**长度边界检查**：

```c
// p: 当前解析位置指针
// end: 缓冲区结束位置指针
// len: 从 QUIC varint 解码出的参数值长度（uint64_t）

if (len > (uint64_t) (end - p))    // 修复后
    return -1;                       // 剩余空间不够，拒绝
```

它的作用是：**在读取参数的值之前，检查剩余缓冲区 `end - p` 是否足够容纳长度为 `len` 的参数值**。如果不够，则返回 -1（解码失败）。

这是传输参数解码中**最关键的安全关卡**——所有参数在进入 switch-case 分发处理之前，都必须先通过这道检查。

---

## 为什么只在 32 位系统上出问题

### 类型分析

| 变量 | 类型 | 32 位系统 | 64 位系统 |
|------|------|-----------|-----------|
| `len` | `uint64_t` | 64-bit **无符号** | 64-bit **无符号** |
| `end - p` | `ptrdiff_t` | **32-bit 有符号** `int32_t` | **64-bit 有符号** `int64_t` |

`end` 和 `p` 都是 `const unsigned char *` 指针，指针减法的结果类型是 `ptrdiff_t`，这取决于平台：
- **32 位**：`ptrdiff_t` = `int32_t`（范围：$-2^{31} \sim 2^{31}-1$）
- **64 位**：`ptrdiff_t` = `int64_t`（范围：$-2^{63} \sim 2^{63}-1$）

### 漏洞触发过程

**有漏洞的代码：** `if ((ptrdiff_t) len > end - p)`

在 **32 位系统**上：

```
攻击者构造 QUIC 包，将某个参数的 len 字段设为 3,000,000,000
（注意：QUIC varint 最大可编码 2^62-1，远超 32 位 ptrdiff_t 的范围）

len = 3,000,000,000  (uint64_t)
         ↓
(ptrdiff_t) len      →  溢出截断为负数！  (-1,294,967,296)
         ↓
 负数  >  end - p    →  永远为 false     ← 边界检查被绕过！
         ↓
后续代码用这个巨型 len 去读内存  →  OOB 越界读取 → 崩溃
```

在 **64 位系统**上：
```
len = 3,000,000,000  (uint64_t)
         ↓
(ptrdiff_t) len      →  3,000,000,000  (正数，无溢出，因为 int64_t 范围远大于此)
         ↓
 3,000,000,000  >  end - p    →  true   ← 边界检查正确拦截！
```

### 为什么 64 位是安全的

你可能会想："如果攻击者把 len 设得更大，比如 $2^{63}$ 呢？"

但在 QUIC 协议中，varint 最大编码值是 $2^{62}-1$（约 $4.6 \times 10^{18}$），而 `int64_t` 的最大值是 $2^{63}-1$（约 $9.2 \times 10^{18}$）。所以即使在极端情况下，`(ptrdiff_t) len` 在 64 位系统上也**永远不会溢出为负数**。

### 修复代码

```c
if (len > (uint64_t) (end - p))    // 两边都是无符号，比较结果永远正确
```

将 `end - p` 强转为 `uint64_t`，使比较双方都是**无符号 64 位整数**，无论在 32 位还是 64 位平台上都能正确工作。

---

### 总结

| 维度 | 说明 |
|------|------|
| **漏洞根因** | `uint64_t` 向 `ptrdiff_t`（32-bit signed）的有损转型导致负数 |
| **触发条件** | 仅在 **32 位** 编译的程序中可触发 |
| **攻击方式** | 构造 QUIC 握手包，将任意传输参数的 length 字段设为 $\geq 2^{31}$ 的值 |
| **后果** | 越界读取 → 拒绝服务（DoS），可能信息泄露 |
| **影响参数** | **所有**传输参数（通用边界检查，非特定参数） |

# Remote DoS

## QPACK 动态表容量的业务场景

### 什么是动态表？

QPACK 是 HTTP/3 的头部压缩协议（类似 HTTP/2 的 HPACK）。它有两张表：

1. **静态表**（Static Table）— 预定义的常见头部，如 `:authority`、`content-type` 等，共 99 项，不可修改
2. **动态表**（Dynamic Table）— 连接过程中动态添加的条目，用于缓存之前出现过的头部，后续请求可以引用而非重复发送

### 动态表容量的作用

`SETTINGS_QPACK_MAX_TABLE_CAPACITY` 是**解码器**（服务端）告诉**编码器**（客户端）自己能承受的动态表最大字节数。

```
解码器 (服务端) ─── SETTINGS_QPACK_MAX_TABLE_CAPACITY=4096 ───→ 编码器 (客户端)
```

**正常业务流程：**

```
请求1: 发送 :authority: example.com  →  服务端缓存此条目
请求2: 引用动态表索引即可           →  无需重复发送 ":authority: example.com" 的全部 24 字节
```

### 真实场景中的容量协商

| 角色 | 限制表容量的原因 |
|------|----------------|
| **服务端** | 动态表占用内存，限制容量防止恶意客户端撑爆内存 |
| **客户端** | 同理，限制解码器端的动态表内存占用 |
| **代理/网关** | 处理大量连接时更需要严格控制每连接内存 |

### 内存计算

```
动态表内存 ≈  Σ(32 + name_len + value_len)  每条目
            ↓
           最多不超过 SETTINGS_QPACK_MAX_TABLE_CAPACITY
```

正常值：`4096`（默认）~ `16384`（常见配置）。可容纳几十到几百个头部条目。

### 攻击利用了哪个环节？

服务端在解码器流上收到 `Set Dynamic Table Capacity = 0` 指令时，会将 `qpd_cur_max_capacity` 设为 0，意图是告诉编码器"我没有空间缓存任何条目了"。

但漏洞代码在做**大小检查**时：
```c
if (val_len > (0 - name_len) << ...)  // 0 - 10 下溢成 42 亿
```

用下溢绕过了这个本该保护内存的检查，导致后续的 `malloc` 不再受容量约束。

## 漏洞代码

```c
// 位置1: Insert With Name Reference (第4636行)
if (WINR.val_len > ((dec->qpd_cur_max_capacity
                    - WINR.name_len) << (WINR.is_huffman << 1)))

// 位置2: Insert Without Name Reference - 值长度 (第4851行)
if (WONR.str_len > ((dec->qpd_cur_max_capacity
        - WONR.entry->dte_name_len) << (WONR.is_huffman << 1)))
```

下溢发生在 `capacity - name_len` 中 `capacity < name_len` 时。

---

## 场景一：Set Dynamic Table Capacity = 0（我们使用的攻击）

```
qpd_cur_max_capacity = 0     ← 通过 Set Capacity 指令设置
name_len = 10                ← 引用静态表 :authority (第0项)
```

```
(0 - 10) → unsigned wraparound → 4294967286
val_len(16777215) > 4294967286  → 永远为假 → 检查通过 → malloc
```

## 场景二：任意 capacity < name_len

如果容量设为小于 name 长度的值，都会下溢。静态表中 name 较长的条目：

| 静态表索引 | name | name_len |
|-----------|------|----------|
| 33 | `access-control-allow-headers` | **28** |
| 34 | `access-control-allow-origin` | **27** |
| 35 | `access-control-allow-methods` | **28** |
| 36 | `access-control-allow-credentials` | **32** |
| 37 | `access-control-expose-headers` | **29** |
| 38 | `access-control-request-headers` | **30** |
| 39 | `access-control-request-method` | **29** |
| 43 | `content-security-policy` | **23** |
| 57 | `strict-transport-security` | **25** |
| 84 | `upgrade-insecure-requests` | **25** |
| 88 | `x-frame-options` | **15** |

例如 `capacity=20`，引用 `access-control-allow-headers`（name_len=28）：
```
(20 - 28) → unsigned wraparound → 4294967288
```

## 场景三：客户端 SETTINGS 中设 QPACK Max Table Capacity = 0

HTTP/3 的 SETTINGS 帧中，客户端可以发送 `SETTINGS_QPACK_MAX_TABLE_CAPACITY = 0`，服务端据此初始化 `qpd_max_capacity = 0`。此时**任何 Insert 指令都不需要先 Set Capacity**，直接触发下溢：

```c
// lsqpack_dec_init() 中:
dec->qpd_cur_max_capacity = dyn_table_size;  // = 0
```

后续 Insert With Name Reference 立即：
```
(0 - name_len) → 下溢
```

## 场景四：Huffman 放大（即使不下溢）

当 `capacity > name_len` 时不发生下溢，但 `<< (is_huffman << 1)` 会放大可允许的 val_len：

- **Huffman=0**（纯文本）: `val_len > (capacity - name_len) × 1`
- **Huffman=1**: `val_len > (capacity - name_len) × 4`

即使不下溢，Huffman 模式允许 val_len 达到 `4 × (capacity - name_len)`，而 `alloced_val_len = val_len + val_len / 2`，实际 malloc 大小 = `val_len × 1.5`，是检查阈值的 **6 倍**。

## 场景五：动态表条目长名称

引用动态表中的条目时，`name_len` 来自该条目的实际名称长度。如果动态表中存在长名称条目，且当前容量小于该长度，同样触发下溢。

```c
// 动态表分支:
WINR.name_len = WINR.reffed_entry->dte_name_len;
// ...
if (WINR.val_len > ((capacity - WINR.name_len) << ...))  // 可能下溢
```

---

## 总结

| 场景 | 触发条件 | 效果 |
|------|---------|------|
| Set Capacity=0 | 发送 `0x20` 指令 | 最直接的攻击方式 |
| SETTINGS 设 capacity=0 | 客户端 SETTINGS 帧 | 全局无容量，所有 Insert 均下溢 |
| 引用静态表长名称 | capacity < name_len (如 15~32) | 用低容量绕过检查 |
| Huffman 放大 | is_huffman=1 | 即使不下溢，可分配 6 倍于阈值的内存 |
| 动态表长名称 | 先插入长名称条目，再设低容量引用 | 同上 |

**根源**: 所有场景的根因是同一个——`unsigned` 减法在 `减数 > 被减数` 时产生回绕，且引入该检查的 commit（`73b010d6`, 2019年）未做前置判断 `if (name_len > capacity) return -1`。