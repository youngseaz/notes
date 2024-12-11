
# DNS

DNS (Domain Name Service) 将域名地转换成 IP 地址，熟知端口为 53


# DNS 相关概念


## DNS VIEW （DNS 视图）

### 视图基本概念

`View` 是 DNS 服务器的一个高级特性，用于根据查询请求的来源或其他条件，每个视图可以包含自己的区域配置、访问控制列表（ACL）以及响应策略，为同一个域名提供不同的 DNS 响应。它是通过将不同的 `view` 与特定的条件匹配来实现的。

### 视图用途

以下是 `view` 的主要作用和常见应用场景（以开源 DNS 软件 BIND 为例）：

1. 基于来源 IP 的条件响应
   - **作用**: BIND 可以根据查询请求的来源 IP 地址或 IP 地址范围（通过 ACL，即访问控制列表）决定将请求定向到哪个 view。
   - **应用场景**: 
     - **内部和外部 DNS 解析**: 企业可以配置两个 views，一个针对内部网络用户（例如，公司局域网），另一个针对外部用户（例如，互联网用户）。内部用户可能会解析 `example.com` 得到内网 IP（例如，`10.0.0.1`），而外部用户则解析得到公网 IP（例如，`203.0.113.1`）。
     - **地理位置优化**: DNS 服务器可以根据查询者的地理位置，提供指向最近数据中心的 IP 地址。这对于 CDN（内容分发网络）或有多个数据中心的全球性企业非常有用。

2. **提供不同级别的访问控制**
   - **作用**: 通过使用不同的 views，可以实现对 DNS 数据的访问控制。例如，某些数据只对特定的 IP 地址范围可见。
   - **应用场景**: 
     - **内部服务保护**: 某些 DNS 记录可能只需要在公司内部可见，例如内网的数据库服务器或内部的应用服务。这些记录可以配置在只对内部 view 可见的 zone 中，而外部用户无法查询到这些记录。

3. **不同的 DNS 策略管理**
   - **作用**: 不同的 views 可以配置不同的 DNS 策略，如不同的缓存策略、转发器配置或解析行为。
   - **应用场景**:
     - **测试和生产环境分离**: 通过配置不同的 views，你可以在同一台 DNS 服务器上管理测试环境和生产环境的 DNS 配置。例如，测试环境的查询可能会转发到测试 DNS 服务器，而生产环境的查询则会使用不同的解析路径。
     - **细化的 DNS 服务管理**: 某些情况下，你可能需要对某些用户提供特定的解析策略，比如强制使用某个转发器或设置特定的 TTL 值，这些都可以通过 views 来实现。

4. **多租户环境中的 DNS 隔离**
   - **作用**: 在多租户环境中（例如，托管服务或云服务），可以使用 views 来隔离不同租户的 DNS 数据。
   - **应用场景**: 
     - **租户数据隔离**: 每个租户都有独立的 view 和 zone，因此不同租户之间的 DNS 记录是完全隔离的，确保一个租户的 DNS 配置不会影响另一个租户。

5. **View 的配置示例**

假设你有一个 `example.com` 的域名，并且需要为内部和外部用户提供不同的 IP 地址，你可以这样配置 views：

```bash
view "internal" {
    match-clients { 10.0.0.0/8; };  # 仅限内部网段
    zone "example.com" {
        type master;
        file "/etc/bind/zones/db.internal.example.com";
    };
};

view "external" {
    match-clients { any; };  # 所有其他用户
    zone "example.com" {
        type master;
        file "/etc/bind/zones/db.external.example.com";
    };
};
```

在这个示例中，`internal` view 针对内网用户，他们会解析到内网的 DNS 记录，而 `external` view 针对其他所有用户，他们会得到外网的 DNS 记录。


## DNS ZONE （DNS 区）


DNS（Domain Name System）区（zone）是DNS中一个管理单位，它代表了DNS命名空间的一部分。每个区由一个特定的DNS服务器负责，称为权威DNS服务器。以下是DNS区的详细描述：

### DNS 区的基本概念

- **Zone（区）：** DNS区是DNS命名空间中的一个子树，它包含了该区域内所有域名的DNS记录。每个DNS区通常对一个或多个域名，如`example.com`。
- **Zone File（区文件）：** DNS区的所有记录都存储在一个或多个文本文件中，这些文件被称为区文件。区文件包含了域名和对应的IP地址、别名、邮件交换器等信息。
- **SOA Record（起始授权记录）：** 每个区文件中必须包含一个SOA记录，定义了区的基本信息，如序列号、主DN服务器、管理员邮箱、刷新间隔等。

### DNS区的类型

- **主区（Primary Zone）：** 主区是一个DNS区的主要副本，包含了该区的所有DNS记录，并且可以进行读写操作主DNS服务器管理主区文件。
- **从区（Secondary Zone）：** 从区是主区的只读副本，从区的DNS服务器通过区传送（zone transfer）从主DN服务器获取数据。它为主区提供了冗余，确保DNS服务的高可用性。
- **转发区（Forward Zone）：** 转发区并不存储DNS记录，而是将DNS查询请求转发给指定的DNS服务器处理。
- **反向区（Reverse Zone）：** 反向区与正向区相对，用于从IP地址解析到域名。这对于网络诊断和反向DNS查询有用。

### DNS记录类型

- **A Record（地址记录）：** 将域名映射到IPv4地址。
- **AAAA Record：** 将域名映射到IPv6地址。
- **CNAME Record（别名记录）：** 为一个域名创建别名，指向另一个域名。
- **MX Record（邮件交换记录）：** 指定域名的邮件服务器。
- **NS Record（名称服务器记录）：** 指定该区的权威DNS服务器。
- **PTR Record（指针记录）：** 用于反向DNS查询，将IP地址映射到域名。
- **TXT Record：** 用于存储任意文本信息，通常用于验证和安全目的（如SPF、DKIM等）。

### 区传送（Zone Transfer）

- **AXFR：** 完整区传送，通常用于将整个区文件从主DNS服务器复制到从DNS服务器。
- **IXFR：** 增量区传送，仅传送自上次传送后更新的记录。

### 动态 DNS 和 TSIG

- **动态DNS（Dynamic DNS）：** 允许实时更新DNS记录，而不需要手动编辑区文件。
- **TSIG（Transaction SIGnature）：** 使用共享密钥对DNS消息进行签名，确保区传送等操作的安全性。

### DNS 区管理工具

- **BIND：** 最常用的DNS服务器软件，广泛用于配置和管理DNS区。
- **rndc：** BIND的远程管理工具，允许管理员对DNS服务进行动态更新、重新加载区等操作。


## DNS 权威区

**权威区**（Authoritative Zone）是指由 DNS 服务器直接管理和负责的 DNS 区域。在权威区内，DNS 服务器是该区域的唯一可信来源，负责存储并提供该区域的 DNS 记录。这意味着当客户端请求与该区域相关的 DNS 信息时，权威 DNS 服务器会提供准确且最新的记录。

### 主要特点

1. **数据来源**：权威区的数据直接存储在权威 DNS 服务器的区域文件中，这些数据包括域名的 A 记录、MX 记录、CNAME 记录等。
   
2. **权威响应**：当权威 DNS 服务器收到针对该区域的查询请求时，它返回的响应被称为**权威响应**（Authoritative Response），这些响应通常会包含一个 `AA`（Authoritative Answer）标志，表明数据来自权威来源。

3. **区域类型**：
   - **主区域（Primary/Master Zone）**：服务器是该区域的主要管理者，存储着该区域的原始数据。任何更改都是在主区域中完成的。
   - **从区域（Secondary/Slave Zone）**：服务器从主服务器获取数据的副本，并定期进行同步。虽然从区域也能提供权威响应，但它的记录副本来源于主服务器。

### 示例

假设你管理的域名是 `example.com`，你可以在 BIND 的 `named.conf` 文件中定义一个主区域（Primary Zone）：

```bash
zone "example.com" {
    type master;
    file "example.com.zone";
};
```

在这个示例中，`example.com` 就是一个权威区。BIND 服务器通过读取 `example.com.zone` 文件中的数据来提供权威的 DNS 记录。

### 区别于非权威区

**非权威区**通常是指递归解析器从其他权威 DNS 服务器获取的缓存数据。当递归解析器响应查询时，如果数据来自缓存而不是其自身管理的区域，则这些数据是非权威的，不具有 `AA` 标志。

### 作用

权威区在 DNS 体系中起到了以下作用：

- **管理 DNS 记录**：你可以直接在权威区中添加、修改或删除域名的 DNS 记录。
- **提供准确的 DNS 信息**：其他 DNS 服务器和客户端依赖于权威区提供的记录来解析域名。
- **支持区域传送**：主权威服务器可以通过区域传送将其数据分发给从服务器，确保冗余和负载均衡。

### 总结

权威区是 DNS 服务器管理的一个关键部分，它确保域名的 DNS 记录是准确且可用的。通过权威区，DNS 服务器能够对外提供权威的 DNS 数据，并确保域名解析的正确性和一致性。



## DNS 配置

`named.conf` 是 BIND DNS 服务器的主配置文件，用于定义 DNS 服务的全局设置、区域定义、访问控制和其他相关配置。下面是 `named.conf` 中所有主要配置参数的详解。

### 1. **全局选项（options）**

`options` 块用于设置全局配置参数，影响整个 BIND 服务器的行为。

```bash
options {
    directory "/var/named";  # 指定存放区域文件的目录
    listen-on port 53 { 127.0.0.1; };  # 指定BIND监听的IP地址和端口
    allow-query { any; };  # 定义允许查询的客户端，默认允许所有
    recursion yes;  # 允许递归查询
    allow-recursion { 127.0.0.1; };  # 指定允许递归查询的客户端
    allow-transfer { none; };  # 定义允许区域传送的客户端
    forwarders { 8.8.8.8; 8.8.4.4; };  # 设置转发器，非权威查询将转发到这些DNS服务器
    dnssec-enable yes;  # 启用DNSSEC功能
    dnssec-validation auto;  # 自动启用DNSSEC验证
    max-cache-size 512M;  # 限制DNS缓存的最大大小
    version "none";  # 隐藏BIND版本信息
};
```

- **`directory`**: 定义存放区域文件的目录。
- **`listen-on`**: 指定 BIND 监听的 IP 地址和端口，默认为 53。
- **`allow-query`**: 定义允许查询的客户端 IP 地址，可以是特定 IP、子网或 `any` 表示所有。
- **`recursion`**: 启用或禁用递归查询。
- **`allow-recursion`**: 定义允许递归查询的客户端。
- **`allow-transfer`**: 指定允许进行区域传送的客户端 IP 地址。
- **`forwarders`**: 设置转发器 IP 地址，BIND 将非权威的查询转发给这些服务器。
- **`dnssec-enable`**: 启用 DNSSEC 功能，用于确保 DNS 数据的真实性。
- **`dnssec-validation`**: 设置 DNSSEC 的验证模式。
- **`max-cache-size`**: 限制 DNS 缓存的最大大小。
- **`version`**: 隐藏或指定 BIND 服务器对外显示的版本信息。

### 2. **区域定义（zone）**

`zone` 块定义了一个特定 DNS 区域的配置，包括主区域、从区域、转发区域等。

```bash
zone "example.com" {
    type master;
    file "example.com.zone";
    allow-transfer { 192.168.1.2; };
    also-notify { 192.168.1.3; };
    allow-update { key "update-key"; };
};
```

- **`type`**: 区域类型，包括 `master`（主区域）、`slave`（从区域）、`forward`（转发区域）、`stub`（存根区域）。
- **`file`**: 指定区域文件的位置。
- **`allow-transfer`**: 定义允许进行区域传送的客户端 IP 地址。
- **`also-notify`**: 在区域更新时通知的其他服务器 IP 地址。
- **`allow-update`**: 指定允许动态更新的客户端，可以是 TSIG 密钥或 IP 地址。

### 3. **视图（view）**

`view` 块允许你根据客户端的 IP 地址或其他条件提供不同的 DNS 视图。

```bash
view "internal" {
    match-clients { 192.168.1.0/24; };
    recursion yes;
    zone "example.com" {
        type master;
        file "example.com.internal.zone";
        allow-update { 192.168.1.1; };
    };
};
```

- **`match-clients`**: 定义哪些客户端可以使用此视图。
- **`recursion`**: 启用或禁用此视图中的递归查询。
- **`zone`**: 在视图中定义特定区域的配置。

### 4. **访问控制列表（acl）**

`acl` 块用于定义一组 IP 地址或子网，供其他配置指令使用。

```bash
acl "trusted" {
    192.168.1.0/24;
    10.0.0.0/8;
};
```

- **`acl`**: 定义一个访问控制列表，可以在 `allow-query`、`allow-transfer` 等指令中引用。

### 5. **日志（logging）**

`logging` 块用于配置 BIND 的日志输出，包括日志类别、通道和输出位置。

```bash
logging {
    channel default_log {
        file "/var/log/named.log" versions 3 size 5m;
        severity info;
        print-time yes;
        print-severity yes;
        print-category yes;
    };
    category default { default_log; };
};
```

- **`channel`**: 定义日志输出通道，包括输出文件、日志轮转、日志级别等。
- **`category`**: 定义日志类别，将其输出到指定的日志通道。

### 6. **密钥（key）**

`key` 块用于定义 TSIG 密钥，用于认证区域传送、动态更新等操作。

```bash
key "rndc-key" {
    algorithm hmac-sha256;
    secret "base64-encoded-secret";
};
```

- **`algorithm`**: 指定密钥的加密算法，如 `hmac-sha256`。
- **`secret`**: 共享密钥的 Base64 编码字符串。

### 7. **控制（controls）**

`controls` 块配置 BIND 的控制接口，用于与 `rndc` 工具通信。

```bash
controls {
    inet 127.0.0.1 port 953 allow { 127.0.0.1; } keys { "rndc-key"; };
};
```

- **`inet`**: 指定控制接口的 IP 地址和端口。
- **`allow`**: 定义允许访问控制接口的 IP 地址。
- **`keys`**: 指定用于认证的 TSIG 密钥。

### 8. **转发（forwarders）**

`forwarders` 用于指定 BIND 在处理非权威查询时转发到的上游 DNS 服务器。

```bash
forwarders {
    8.8.8.8;
    8.8.4.4;
};
```

- **`forwarders`**: 列出转发查询的上游 DNS 服务器 IP 地址。

### 9. **限制（rate-limit）**

`rate-limit` 块用于设置 BIND 的查询速率限制，以防止 DoS 攻击。

```bash
rate-limit {
    responses-per-second 10;
    slip 2;
};
```

- **`responses-per-second`**: 设置每秒钟允许的最大查询响应数。
- **`slip`**: 设置丢弃响应前的查询次数。

### 10. **动态 DNS（dynamic DNS）**

`allow-update` 指令用于指定哪些客户端可以动态更新区域记录。

```bash
allow-update { key "update-key"; };
```

- **`allow-update`**: 允许动态更新的客户端，可以是 IP 地址或 TSIG 密钥。

### 11. **通知（notify）**

`notify` 指令用于指定在区域更新时是否发送通知给从服务器。

```bash
notify yes;
```

- **`notify`**: `yes` 或 `no`，决定是否通知从服务器。

### 12. **解析器配置（resolver）**

用于配置 BIND 的递归解析行为，通常在 ISP 或企业级 BIND 服务器中使用。

```bash
resolver {
    query-source address * port 53;
};
```

- **`query-source`**: 指定递归查询的源地址和端口。

### 13. **DNSSEC 相关配置**

```bash
dnssec-enable yes;
dnssec-validation auto;
dnssec-lookaside auto;
```

- **`dnssec-enable`**: 启用 DNSSEC。
- **`dnssec-validation`**: 自动启用 DNSSEC 验证。
- **`dnssec-lookaside`**: 启用 DNSSEC 查阅，通常设置为 `auto`。

### 14. **根提示文件（root hints）**

`named.conf` 中可以指定根提示文件的位置，以便 BIND 查找根 DNS 服务器。

```bash
zone "." {
    type hint;
    file "named.root";
};
```

- **`type hint`**: 指定根提示类型。
- **`file`**: 指定根提示文件的位置。

### 15. **转发区域（forward zone）**

用于指定特定区域的转发设置。

```bash
zone "example.org" {
    type forward;
    forwarders { 8.8.8.8; 8.8.4.4; };
};
```

- **`type forward`**: 指定区域类型为转发。
- **`forward

ers`**: 设置此区域的特定转发器。

### 16. **缓存控制**

通过 `max-cache-size` 控制缓存的大小。

```bash
max-cache-size 512M;
```

- **`max-cache-size`**: 限制缓存的最大大小。

### 总结

BIND 的 `named.conf` 配置文件提供了丰富的配置选项，可以灵活地配置 DNS 服务器的行为。通过合理的配置，你可以优化 DNS 性能、增强安全性，并实现复杂的 DNS 解析策略。

