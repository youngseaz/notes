


# 前置知识


## BPF

### BPF 简介
Berkeley Packet Filter (BPF) 最早版本的 BPF 是 1990 年代由 Berkeley 大学开发，用于高效地从网络接口中抓包，主要用于工具如 tcpdump.

extended BPF (eBPF) 是 BPF 的现代增强版，功能大幅扩展，早已超越原始的网络包过滤用途。eBPF 兼容 BPF.

| 特性     | BPF（经典 BPF）       | eBPF（扩展 BPF）                         |
| ------ | ----------------- | ------------------------------------ |
| 最初用途   | 抓包过滤（如 `tcpdump`） | 内核级编程平台（网络、安全、追踪、监控等）                |
| 指令集    | 简单、少数指令           | 丰富、支持调用 helper 函数、更多寄存器              |
| 程序大小限制 | 很小（\~4096 字节）     | 更大（\~1M），允许复杂逻辑                      |
| 执行上下文  | 网络包捕获             | 内核挂钩（kprobe、tracepoint、XDP、LSM 等）    |
| 安全机制   | 无                 | 有：Verifier 校验程序安全性                   |
| 编程语言支持 | 汇编                | C（通过 LLVM）、bpftrace、Python（bcc）等     |
| 内核集成程度 | 较低                | 高度集成，可与多种内核子系统配合                     |
| 数据交互   | 无 map、共享数据机制      | 有 map、ringbuf、perf buffer 等与用户空间交互机制 |
| 状态管理   | 无                 | 支持持久状态（通过 BPF map）                   |


### BPF 原理

[BPF document](https://docs.kernel.org/bpf/)

cBPF VM 架构

1、寄存器
cBPF（Classic BPF）架构非常简洁，只有 2 个 32 位寄存器：
| 寄存器   | 名称                    | 作用                           |
| ----- | --------------------- | ---------------------------- |
| **A** | Accumulator（累加器）      | 所有算术运算、比较、加载/存储操作主要在这个寄存器上进行 |
| **X** | Index Register（索引寄存器） | 作为辅助寄存器，用于索引访问、部分算术运算、条件跳转等  |
同时还有M[0..15]：16 个 32 位 scratch memory 槽（临时变量存储）

2、数据流：
数据包缓冲区 → 按需加载到 A / X → 运算 / 比较 → 最终返回匹配或丢弃

3、指令集：
- 加载 / 存储（LD, LDX, ST, STX）
- 算术（ADD, SUB, MUL, DIV, AND, OR, LSH, RSH）
- 跳转（JA, JEQ, JGT, JGE, JSET）
- 返回（RET）
- 杂项（TAX, TXA）

特点：寄存器极少，模型简单，只能访问数据包内容和 scratch memory。返回值只有两种：丢弃包 / 接收包（可指定最大长度）

### BPF 应用

Classic BPF（cBPF）代码，用于创建一个 Linux 原始套接字的 BPF 数据包过滤器
```c
struct sock_filter {
    __u16 code; // 操作码（指令）
    __u8 jt;    // 条件跳转成功时跳几条
    __u8 jf;    // 条件跳转失败时跳几条
    __u32 k;    // 常数参数
};
```


## IP 分片

当 IP 包大小超过路径某段链路的最大传输单元 (max transmission unit, MTU) 且允许分片（DF=0）时，IP 层就会进行分片。

IP 分片（Fragmentation） 是指：当一个 IP 包的大小（总长度）超过了沿途某段链路的 MTU（最大传输单元），就必须将这个包拆成多个碎片传输，以适应链路的最大包长限制。

IP 数据包会在满足 以下情况时发生分片（Fragmentation）：

🚧 二、什么情况下会触发 IP 分片？
- 条件 1：IP 数据包长度 > 路径上的某个 MTU，常见 MTU：以太网默认是 1500 字节；
- 条件 2：该 IP 包允许分片（Don't Fragment = 0）。IP 报文头中的 Flags 字段有一位叫 DF（Don't Fragment）：
```
Flag 位	含义
DF = 1	不允许分片，若不能传就丢弃并回 ICMP
DF = 0	可以分片
```
要触发真正的“IP 分片”，两个条件都要满足：IP包长度 > MTU 且 DF=0
🧪 三、分片字段（IP头）
分片时，IP 包头的这几个字段特别关键：

字段名|含义
-|-
Identification	| 所有分片有相同的 ID，用于重组
Fragment Offset	| 分片偏移量（单位为 8 字节）
MF（More Fragments）|	除最后一个分片外都设为 1，最后一个为 0
DF（Don't Fragment）|	设置为 1 时不允许分片

![alt text](<images/01 BPFDoor 原理/image-2.png>)

### IP 分片安全问题

攻击者可能利用分片：
- 绕过防火墙（IP分片重组后的 payload 被分散）
- 构造 overlapping fragments → 触发协议实现漏洞（Teardrop 攻击）
- BPFDoor 类木马使用分片包绕过过滤器

# BPFDoor 详细解析

- [BPF Instruction Set Architecture](https://www.kernel.org/doc/html/latest/bpf/standardization/instruction-set.html)
- [bpfdoor source code - github](https://github.com/gwillgues/BPFDoor/blob/main/bpfdoor.c)

```c
struct sock_filter bpf_code[] = {
                { 0x28, 0, 0, 0x0000000c },   // 01 ldh[12], 加载以太网帧第 12 字节开始的 2 字节内容，也就是 EtherType。
                { 0x15, 0, 27, 0x00000800 },  // 02 jeq #0x0800, jt=0, jf=27
                { 0x30, 0, 0, 0x00000017 },   // 03 ldb [23] 加载 IP 数据包第 23 字节，即 协议字段（protocol）
                { 0x15, 0, 5, 0x00000011 },   // 04 jeq #17, jt=0, jf=5 判断协议是否为 0x11 → UDP。不是就跳 5 条（丢弃该路径）。
                { 0x28, 0, 0, 0x00000014 },   // 05 ldh [20] 从 IP 数据开始第 20 字节读 2 字节 → 即 IP flags/fragment offset 字段。
                { 0x45, 23, 0, 0x00001fff },  // 06 jset #0x1fff, jt=23, jf=0 判断是否是分片包（低 13 位不为 0 表示是分片包），如果是，就跳转 23（丢弃）。
                { 0xb1, 0, 0, 0x0000000e },   // 07 ldx 4*([14] & 0x0f)X = IP 头部长度（字节）
                { 0x48, 0, 0, 0x00000016 },   // 08 ldh [22] 从UDP头部取源端口（以太网头14字节+IP头长度X，22偏移是UDP源端口位置）
                { 0x15, 19, 20, 0x00007255 }, // 09 jeq #29269 (端口 29269)，如果端口是29269，往后跳19条指令，否则往后跳20
                { 0x15, 0, 7, 0x00000001 },   // 10 jeq #1  如果 proto == 1 (ICMP) → 跳到 10；否则 → 跳到 9+1+7=17
                { 0x28, 0, 0, 0x00000014 },   // 11 ldh [20]（IPv4 Flags+Fragment offset）
                { 0x45, 17, 0, 0x00001fff },  // 12 jset #0x1fff 有分片 → 跳到 11+1+17=29；否则继续
                { 0xb1, 0, 0, 0x0000000e },   // 13 ldxh 4*([14]&0xf)IP 头部长度
                { 0x48, 0, 0, 0x00000016 },   // 14 ldh [22] ICMP 类型和代码
                { 0x15, 0, 14, 0x00007255 },  // 15 jeq #0x7255 判断值是否 == 29269
                { 0x50, 0, 0, 0x0000000e },   // 16 ld [14] 加载 4 字节（某个 IP 首部字段）
                { 0x15, 11, 12, 0x00000008 }, // 17 jeq #0x8 是否 == 8
                { 0x15, 0, 11, 0x00000006 },  // 18 jeq #0x6 是否 == 6 (TCP)
                { 0x28, 0, 0, 0x00000014 },   // 19 ldh [20] IP 标志+片偏移
                { 0x45, 9, 0, 0x00001fff },   // 20 jset #0x1fff 检查分片
                { 0xb1, 0, 0, 0x0000000e },   // 21 ldxh 4*([14]&0xf) IP 头长度
                { 0x50, 0, 0, 0x0000001a },   // 22 ld [26] 加载 TCP 目标端口
                { 0x54, 0, 0, 0x000000f0 },   // 23 and #0xf0 按位与掩码 0xf0
                { 0x74, 0, 0, 0x00000002 },   // 24 lsh #2 左移 2 位
                { 0xc, 0, 0, 0x00000000 },    // 25 tax A → X
                { 0x7, 0, 0, 0x00000000 },    // 26 ldh [14] 取某字段
                { 0x48, 0, 0, 0x0000000e },   // 27 ldh [14] 取某字段
                { 0x15, 0, 1, 0x00005293 },   // 28 jeq #0x5293 是否 == 21139
                { 0x6, 0, 0, 0x0000ffff },    // 29 ret #0xffff  接收数据包
                { 0x6, 0, 0, 0x00000000 },    // 30 ret #0x0 丢弃数据包
        };
```

```
以太网类型 == IPv4? 
 ├─否 → 丢包
 └─是 → 协议字段?
      ├─UDP → 分片? → 否 → 端口=29269? → 是=接收 否=丢
      ├─ICMP → 分片? → 否 → identifier=29269? → 是=接收 否=丢
      └─TCP → 分片? → 否 → 端口匹配特定规则? → 是=接收 否=丢


// step 1: 读取以太类型
if (ether_type != 0x0800) {     // 不是 IPv4
    drop();                     // 丢弃
}

// step 2: 读取 IP 协议号
if (ip_proto == 0x11) {         // UDP
    // step 3: 检查是否有分片
    if (ip_fragment_offset & 0x1fff) {
        drop();
    }
    // step 4: 获取 UDP 目标端口
    if (udp_dst_port == 29269) {
        accept();               // UDP 且目标端口是 29269
    } else {
        drop();
    }
}

// step 5: 如果不是 UDP，则判断是否 ICMP
if (ip_proto == 0x01) {         // ICMP
    if (ip_fragment_offset & 0x1fff) {
        drop();
    }
    // step 6: 读取 ICMP 类型/代码字段
    if (icmp_type_code == 29269) {
        accept();
    } else {
        drop();
    }
}

// step 7: 如果不是 UDP/ICMP，则判断是否 TCP
if (ip_proto == 0x06) {         // TCP
    if (ip_fragment_offset & 0x1fff) {
        drop();
    }
    // step 8: 从 TCP 头部读取目标端口
    // 这里有一段掩码、移位、X 寄存器操作（可能是从 TCP flags/offset 计算）
    // 最终比较某字段是否等于 0x5293
    if (tcp_field == 0x5293) {
        accept();
    } else {
        drop();
    }
}

// 其他协议全部丢弃
drop();


```


![alt text](<images/01 BPFDoor 原理/image.png>)

![alt text](<images/01 BPFDoor 原理/image-1.png>)
