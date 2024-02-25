OpenVPN 有两种工作模式，分别为 TUN(Tunnel) 和 TAP(Terminal Access Point) 模式，这两种模式的原理和应用范围如下

# TUN 工作模式

TUN 模式工作方式是三层，用于 IP 路由转发，VPN 地址和内网地址处于不同网段

![](<images/01 OpenVPN的工作模式/image-5.png>)

Windows 修改注册表项，允许网卡直接 IP 路由转发，**服务端和客户端都要修改**
> HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Services\Tcpip\Parameters 的 IPEnableRouter 改为 1

![](<images/01 OpenVPN的工作模式/image.png>)


# TAP 工作模式

TAP 工作模式工作方式是二层，用于拓展内网，客户端和服务端形式上处于一个局域网。拓扑如下

![](<images/01 OpenVPN的工作模式/image-2.png>)





